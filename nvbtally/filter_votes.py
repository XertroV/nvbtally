__author__ = 'xertrov'

# run like:
# $ python -m nvbtally.updater

from binascii import unhexlify, hexlify
import argparse

from sqlalchemy.orm import sessionmaker

from blockchain.blockexplorer import get_tx

from .coinsecrets import get_block_range, get_blocks
from .models import engine, Nulldata, FilteredNulldata, RawVote


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

    def run(self):

        def get_unfiltered():
            filtered_ids = self.session.query(FilteredNulldata.nulldata_id)
            return self.session.query(Nulldata).filter(~Nulldata.id.in_(filtered_ids)).all()

        get_addrs_for = {}

        for nulldata in get_unfiltered():
            self.session.add(FilteredNulldata(nulldata_id=nulldata.id))
            if nulldata_filter(nulldata):
                self.session.add(RawVote(nulldata_id=nulldata.id))
                get_addrs_for.add(nulldata)

        self.session.commit()





parser = argparse.ArgumentParser()
parser.add_argument('--watch', help='Watch for changes and update', action='store_true')
args = parser.parse_args()

if __name__ == "__main__":
    f = Filterer()
    f.run()
