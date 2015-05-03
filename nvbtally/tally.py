__author__ = 'xertrov'

# run like:
# $ python -m nvbtally.tally -h

from binascii import unhexlify, hexlify
import argparse
from time import sleep
import logging

from sqlalchemy.orm import sessionmaker

from blockchain.blockexplorer import get_tx

from pycoin.encoding import a2b_base58

from nvblib import instruction_lookup, op_code_lookup, get_op
from nvblib import CreateNetwork, CastVote, DelegateVote, EmpowerVote, ModResolution

from .coinsecrets import get_block_range, get_blocks
from .models import engine, Nulldata, FilteredNulldata, RawVote, Vote, ProcessedVote, Resolution, ValidVoter, NetworkSettings, Delegate


import logging

logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.ERROR)


class Tallier:

    def __init__(self):
        self.Session = sessionmaker(bind=engine)
        self.session = self.Session()
        self.network_settings = None
        self.reset_network_settings()

    def reset_db(self):
        engine.execute("DROP TABLE processed_votes")
        engine.execute("DROP TABLE network_settings")
        engine.execute("DROP TABLE resolutions")
        engine.execute("DROP TABLE valid_voters")
        engine.execute("DROP TABLE votes")

    def find_votes_or_delegates_and_carry(self, l_address_pairs, resolution):
        votes = []
        delegates = []
        for address, carry in l_address_pairs:
            vote = self.session.query(Vote).filter(Vote.nulldata.address == address and Vote.res_name == resolution.res_name).first()
            if vote is None:
                delegate = self.session.query(ValidVoter).filter(ValidVoter.address == address).one().delegate
                if delegate is None:
                    pass  # explicitly abstain
                else:
                    delegates.append((delegate, carry))
            else:
                votes.append((vote.nulldata.address, vote.voter.votes_empowered, vote.vote_num))
        return votes, delegates

    def resolve_resolution(self, resolution):
        self._assert(resolution.resolved is False, 'resolve_resolution(): Resolution must not be resolved')
        valid_voters = self.session.query(ValidVoter).all()
        addresses = [v.address for v in valid_voters]
        l_address_pairs = [(a, a) for a in addresses]
        votes = []
        while len(l_address_pairs) > 0:
            vs, ds = self.find_votes_or_delegates_and_carry(l_address_pairs, resolution)
            l_address_pairs = list(filter(lambda t: t[0] != t[1], ds))
            votes.extend(vs)
        votes_for = sum(map(lambda v: v[1] * v[2], votes))
        votes_total = sum(map(lambda v: v[1] * 255, votes))
        resolution.votes_for = votes_for
        resolution.votes_total = votes_total
        resolution.resolved = True

    def reset_network_settings(self):
        self.network_settings = self.session.query(NetworkSettings).filter(NetworkSettings.id == 1).first()

    def _assert(self, condition, msg):
        if not condition:
            raise Exception(msg)

    def run(self, admin_address, network_name, watch=False, sleep_for=30):

        self.reset_network_settings()

        def get_unprocessed():
            processed_raw_vote_ids = self.session.query(ProcessedVote.raw_vote_id)
            return self.session.query(RawVote).filter(~RawVote.id.in_(processed_raw_vote_ids)).all()

        def resolve_if_earlier_than(ts, commit=False):
            to_resolve = self.session.query(Resolution).filter(Resolution.resolved == False and Resolution.end_timestamp < ts).all()
            list(map(self.resolve_resolution, to_resolve))
            if commit:
                self.session.commit()

        # oh my god this is a mess!
        def apply(op, nulldata):
            self.session.commit()  # commit to begin with so we know there's nothing in the transaction as we'll be rolling back
            try:
                op_type = type(op)
                if self.network_settings is None and op_type == CreateNetwork:
                    print(network_name, op.name, admin_address, a2b_base58(nulldata.address))
                    self._assert(op.name == network_name, 'network name must match during creation')
                    self._assert(a2b_base58(nulldata.address) == admin_address, 'admin address must match during creation')
                    self.session.add(NetworkSettings(admin_address=nulldata.address, network_name=network_name))
                    self.session.commit()
                    self.reset_network_settings()
                    self._assert(self.network_settings is not None, 'Network settings sanity check failed')
                elif self.network_settings is not None and op_type != CreateNetwork:
                    resolve_if_earlier_than(nulldata.timestamp, commit=False)  # resolve any resolutions that are in the past an unresolved, do not commit as if this tx is not valid the resolution should not be processed!

                    # this is the main operation centre
                    if op_type == CastVote:
                        resolution = self.session.query(Resolution).filter(Resolution.res_name == op.resolution).one()
                        voter = self.session.query(ValidVoter).filter(ValidVoter.address == nulldata.address).one()
                        self.session.merge(Vote(vote_num=op.vote_number, res_name=resolution.res_name, nulldata_id=nulldata.id, voter_id=voter.id))
                    elif op_type == EmpowerVote:
                        self._assert(nulldata.address == self.network_settings.admin_address, 'Admin required')
                        self.session.merge(ValidVoter(address=op.address_pretty(), votes_empowered=op.votes))
                    elif op_type == DelegateVote:
                        original_voter = self.session.query(ValidVoter).filter(ValidVoter.address == nulldata.address).one()
                        delegate_voter = self.session.query(ValidVoter).filter(ValidVoter.address == op.address_pretty()).first()
                        if delegate_voter is None:
                            self.session.merge(ValidVoter(address=op.address_pretty(), votes_empowered=0))  # allowed to make a valid voter with 0 on new delegation
                            delegate_voter = self.session.query(ValidVoter).filter(ValidVoter.address == op.address_pretty()).one()
                        self.session.merge(Delegate(voter_id=original_voter.id, delegate_id=delegate_voter.id))
                    elif op_type == ModResolution:
                        self._assert(nulldata.address == self.network_settings.admin_address, 'Requires Admin')
                        self.session.merge(Resolution(res_name=op.resolution, url=op.url, end_timestamp=op.end_timestamp, categories=op.categories))

                else:
                    raise Exception('Wrong time for instruction')
                self.session.commit()  # if we get to the end commit
                print('Success:', nulldata.script, 'committed')
            except Exception as e:
                print('Failed:', nulldata.script, e.__class__, e)
            finally:
                # if something is wrong do not commit, if we already commit()'d this does nothing
                self.session.rollback()

        def process_new():
            unprocd = get_unprocessed()
            to_apply_list = [(v.nulldata.height, v.nulldata.txid, v.nulldata.script, v) for v in unprocd]
            to_apply_list.sort()
            for h, txid, hex_script, v in to_apply_list:
                op_bytes = unhexlify(hex_script)[2:]  # drop OP_RETURN and length
                try:
                    instruction = op_code_lookup(get_op(op_bytes)).from_bytes(op_bytes)
                    apply(instruction, v.nulldata)
                except Exception as e:
                    print('Failed:', hex_script, e.__class__, e)
            for h, txid, hex_script, v in to_apply_list:
                self.session.add(ProcessedVote(raw_vote_id=v.id))
            self.session.commit()


        process_new()

        while watch:
            print("Sleeping for %d seconds." % sleep_for)
            sleep(sleep_for)
            process_new()



parser = argparse.ArgumentParser()
parser.add_argument('--watch', help='Watch for changes and update', action='store_true')
parser.add_argument('--reset-db', help='Reset DB tables corresponding to TALLIED votes', action='store_true')
parser.add_argument('--set-admin', help='Set admin address', type=str, default=None)
parser.add_argument('--set-name', help='Set network name (hex encoded)', type=str, default=None)
args = parser.parse_args()

if __name__ == "__main__":
    tallier = Tallier()
    if args.reset_db:
        tallier.reset_db()
    else:
        if args.set_admin is None and args.set_name is None:
            try:
                admin, name = tallier.network_settings.admin_address, tallier.network_settings.network_name
            except AttributeError as e:
                print(e)
                print('If network is not initialized please manually set network admin ')
        else:
            if args.set_name is None or args.set_admin is None:
                raise argparse.ArgumentError('if --set-admin is used, --set-name is required, and vice versa')
            admin, name = (a2b_base58(args.set_admin), unhexlify(args.set_name))
        tallier.run(admin, name, watch=args.watch)
