#!/usr/bin/env python3
__author__ = 'xertrov'

# run like:
# $ python -m nvbtally.tally -h

from binascii import unhexlify, hexlify
import argparse
from time import sleep

from sqlalchemy.orm import sessionmaker
from sqlalchemy import desc

from pycoin.encoding import a2b_base58

from nvblib import instruction_lookup, op_code_lookup, get_op
from nvblib import CreateNetwork, CastVote, DelegateVote, EmpowerVote, ModResolution, EnableTransfer, DisableTransfer, TransferIdentity
from nvblib.constants import ENDIAN

from .models import engine, Nulldata, FilteredNulldata, RawVote, Vote, ProcessedVote, Resolution, ValidVoter, NetworkSettings, Delegate, TransferEnabled, Transfers, tally_tables

import logging

logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.ERROR)

admin_default = a2b_base58('13MRso7BA6AxEye7PrfT6TdzVHXLZ2DCD5')
name_default = b'\x04test'


class Tallier:

    def __init__(self):
        self.Session = sessionmaker(bind=engine)
        self.session = self.Session()
        self.network_settings = None
        self.reset_network_settings()

    def reset_db(self):
        for table in tally_tables:
            engine.execute("DROP TABLE %s" % table.__tablename__)
            print("Dropping %s" % table.__tablename__)

    def find_votes_or_delegates_and_carry(self, l_address_pairs, resolution):
        votes = []
        delegates = []
        for address, carry, seen in l_address_pairs:
            vote = self.session.query(Vote).filter(Vote.res_name == resolution.res_name).filter(Vote.address == address).order_by(desc(Vote.height)).first()
            if vote is None:
                voter = self.session.query(ValidVoter).filter(ValidVoter.address == address).one()
                delegate_record = self.session.query(Delegate).filter(Delegate.voter_id == voter.id).first()
                delegate_id = delegate_record.delegate_id if delegate_record is not None else delegate_record
                delegate = self.session.query(ValidVoter).filter(ValidVoter.id == delegate_id).one() if delegate_id is not None else None
                if delegate is None:
                    pass  # explicitly abstain
                else:
                    seen.add(address)
                    delegates.append((delegate.address, carry, seen))
            else:
                empowerment = self.session.query(ValidVoter).filter(ValidVoter.address == carry).one().votes_empowered
                votes.append((vote.address, empowerment, vote.vote_num))
        return votes, delegates

    def resolve_resolution(self, resolution, final=True):
        self._assert(resolution.resolved == 0, 'resolve_resolution(): Resolution must not be resolved')
        valid_voters = self.session.query(ValidVoter).all()
        addresses = [v.address for v in valid_voters]
        l_address_pairs = [(a, a, set()) for a in addresses]
        votes = []
        while len(l_address_pairs) > 0:
            vs, ds = self.find_votes_or_delegates_and_carry(l_address_pairs, resolution)
            l_address_pairs = list(filter(lambda t: not t[0] in t[2], ds))  # filter out
            votes.extend(vs)
        votes_for = sum(map(lambda v: v[1] * v[2], votes))
        votes_total = sum(map(lambda v: v[1] * 255, votes))
        resolution.votes_for = votes_for
        resolution.votes_total = votes_total
        if final:
            resolution.resolved = 1
            print("resolving: %s, %d for, %d total" % (resolution.res_name, resolution.votes_for, resolution.votes_total))
        else:
            print("predicting res: %s, %d for, %d total" % (resolution.res_name, resolution.votes_for, resolution.votes_total))


    def reset_network_settings(self):
        self.network_settings = self.session.query(NetworkSettings).filter(NetworkSettings.id == 1).first()

    def mark_superseded(self, address, res_name):
        def mark(vote):
            vote.superseded = True
        list(map(mark, self.session.query(Vote).filter(Vote.address == address).filter(Vote.res_name == res_name).all()))

    def set_default_delegate(self, address):
        voter_id = self.session.query(ValidVoter.id).filter(ValidVoter.address == address).one()[0]
        if self.session.query(Delegate).filter(Delegate.voter_id == voter_id).first() is None:
            self.session.merge(Delegate(voter_id=voter_id, delegate_id=voter_id))

    def _assert(self, condition, msg):
        if not condition:
            raise Exception(msg)

    def voter_from_address(self, address):
        return self.session.query(ValidVoter).filter(ValidVoter.address == address).one()

    def voter_from_address_or_none(self, address):
        return self.session.query(ValidVoter).filter(ValidVoter.address == address).first()

    def assert_admin(self, address):
        self._assert(address == self.network_settings.admin_address, 'Requires Admin')

    def op_cast_vote(self, op, nulldata):
        resolution = self.session.query(Resolution).filter(Resolution.res_name == op.resolution).one()
        self._assert(nulldata.timestamp < resolution.end_timestamp, 'Cannot modify a vote for a resolution that has finished.')
        voter = self.voter_from_address(nulldata.address)
        self.mark_superseded(voter.address, resolution.res_name)
        self.session.merge(Vote(vote_num=int.from_bytes(op.vote_number, ENDIAN), res_name=resolution.res_name, nulldata_id=nulldata.id, voter_id=voter.id, address=nulldata.address, height=nulldata.height))
        self.resolve_resolution(resolution, final=False)

    def op_empower_vote(self, op, nulldata):
        self.assert_admin(nulldata.address)
        empowering_voter = self.voter_from_address_or_none(op.address_pretty())
        if empowering_voter is None:
            self.session.merge(ValidVoter(address=op.address_pretty(), votes_empowered=int.from_bytes(op.votes, ENDIAN)))
        else:
            self.session.merge(ValidVoter(id=empowering_voter.id, address=op.address_pretty(), votes_empowered=int.from_bytes(op.votes, ENDIAN)))
        self.set_default_delegate(op.address_pretty())

    def op_delegate_vote(self, op, nulldata):
        original_voter = self.voter_from_address(nulldata.address)
        delegate_voter = self.session.query(ValidVoter).filter(ValidVoter.address == op.address_pretty()).first()
        if delegate_voter is None:
            self.session.merge(ValidVoter(address=op.address_pretty(), votes_empowered=0))  # allowed to make a valid voter with 0 on new delegation
            delegate_voter = self.voter_from_address(op.address_pretty())
            self.set_default_delegate(op.address_pretty())
        self.session.merge(Delegate(voter_id=original_voter.id, delegate_id=delegate_voter.id))

    def op_mod_resolution(self, op, nulldata):
        self.assert_admin(nulldata.address)
        # test there are no resolved resolutions matching op.resolution
        self._assert(self.session.query(Resolution).filter(Resolution.res_name == op.resolution).filter(Resolution.resolved == 1).first() is None, 'Cannot modify a resolved resolution')
        self.session.merge(Resolution(res_name=op.resolution, url=op.url, end_timestamp=int.from_bytes(op.end_timestamp, ENDIAN), categories=int.from_bytes(op.categories, ENDIAN), resolved=0))

    def op_enable_transfer(self, op, nulldata):
        voter = self.voter_from_address(nulldata.address)
        self.session.merge(TransferEnabled(voter_id=voter.id, transfer_enabled=True))
        self.session.merge(Transfers(voter_id=voter.id, after_time=nulldata.timestamp+24*60*60, new_address=op.address_pretty()))

    def op_transfer(self, op, nulldata):
        voter = self.voter_from_address(nulldata.address)
        transfer_enabled = self.session.query(TransferEnabled).filter(TransferEnabled.voter_id == voter.id).one()
        transfer_details = self.session.query(Transfers).filter(Transfers.voter_id == voter.id).one()
        self._assert(transfer_details.after_time <= nulldata.timestamp, 'Transfer only triggerable after 24 hours')
        self._assert(transfer_enabled.transfer_enabled is True, 'Transfer must be enabled for this identity')

    def op_disable_transfer(self, op, nulldata):
        voter = self.voter_from_address(nulldata.address)
        self.session.merge(TransferEnabled(voter_id=voter.id, transfer_enabled=False))

    def run(self, admin_address=admin_default, network_name=name_default, watch=False, sleep_for=30):

        self.reset_network_settings()

        def get_unprocessed():
            processed_raw_vote_ids = self.session.query(ProcessedVote.raw_vote_id)
            return self.session.query(RawVote).filter(~RawVote.id.in_(processed_raw_vote_ids)).all()

        def resolve_if_earlier_than(ts, commit=False):
            to_resolve = self.session.query(Resolution).filter(Resolution.resolved == 0).filter(Resolution.end_timestamp < ts).all()
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
                        self.op_cast_vote(op, nulldata)
                    elif op_type == EmpowerVote:
                        self.op_empower_vote(op, nulldata)
                    elif op_type == DelegateVote:
                        self.op_delegate_vote(op, nulldata)
                    elif op_type == ModResolution:
                        self.op_mod_resolution(op, nulldata)
                    elif op_type == EnableTransfer:
                        self.op_enable_transfer(op, nulldata)
                    elif op_type == DisableTransfer:
                        self.op_disable_transfer(op, nulldata)
                    elif op_type == TransferIdentity:
                        self.op_transfer(op, nulldata)
                else:
                    raise Exception('Wrong time for instruction')
                self.session.commit()  # if we get to the end commit
                print('Success:', op.decode(), 'committed')
            except Exception as e:
                print('Failed:', op.decode(), e.__class__, e)
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
parser.add_argument('--use-default', help='Use default network params', action='store_true')
args = parser.parse_args()

if __name__ == "__main__":
    tallier = Tallier()
    if args.reset_db:
        tallier.reset_db()
    else:
        if args.set_admin is None and args.set_name is None:
            if args.use_default:
                admin, name = admin_default, name_default
            else:
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
