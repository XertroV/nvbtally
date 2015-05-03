__author__ = 'xertrov'

# run like:
# $ python -m nvbtally.filter_votes -h

from binascii import unhexlify, hexlify
import argparse
from time import sleep
import logging

from sqlalchemy.orm import sessionmaker

from blockchain.blockexplorer import get_tx

from .coinsecrets import get_block_range, get_blocks
from .models import engine, Nulldata, FilteredNulldata, RawVote


def find_address_for_nulldata(nd, tx):
    matches = []
    for i, output in enumerate(tx.outputs):
        if output.script == nd.script:
            matches.append(i)
    if len(matches) == 0:
        return None
    if len(matches) == 1:
        return tx.inputs[matches[0]].address
    raise Exception('unmatched nulldata to identity')

def nulldata_filter(nd):
    b_script = unhexlify(nd.script)
    if b_script[0:1] != b'\x6a':
        return False
    if b_script[2:5] != b'NVB':
        return False
    print(b_script)
    return True


class Filterer:

    def __init__(self):
        self.Session = sessionmaker(bind=engine)
        self.session = self.Session()

    def reset_db(self):
        engine.execute("DROP TABLE filtered_nulldatas")
        engine.execute("DROP TABLE raw_votes")

    def run(self, watch=False, sleep_for=30):

        def get_unfiltered():
            filtered_ids = self.session.query(FilteredNulldata.nulldata_id)
            return self.session.query(Nulldata).filter(~Nulldata.id.in_(filtered_ids)).all()

        def add_unfiltered():
            get_addrs_for = set()

            for nulldata in get_unfiltered():
                self.session.add(FilteredNulldata(nulldata_id=nulldata.id))
                if nulldata_filter(nulldata):
                    self.session.add(RawVote(nulldata_id=nulldata.id))
                    get_addrs_for.add(nulldata)

            self.session.commit()

            for nd in get_addrs_for:
                tx = get_tx(tx_id=nd.txid)  # this is REALLY slow, TODO : parallelize like coinsecrets.
                nd.address = find_address_for_nulldata(nd, tx)
                self.session.commit()
                logging.info("Set nd.address of %d to %s" % (nd.id, nd.address))

        add_unfiltered()

        while watch:
            print("Sleeping for %d seconds." % sleep_for)
            sleep(sleep_for)
            add_unfiltered()





parser = argparse.ArgumentParser()
parser.add_argument('--watch', help='Watch for changes and update', action='store_true')
parser.add_argument('--reset-db', help='Reset DB tables corresponding to FILTERED nulldatats and votes', action='store_true')
args = parser.parse_args()

if __name__ == "__main__":
    f = Filterer()
    if args.reset_db:
        f.reset_db()
    else:
        f.run(watch=args.watch)
