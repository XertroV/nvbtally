__author__ = 'xertrov'

# run like:
# $ python -m nvbtally.updater

from queue import Queue
from time import sleep, time
import argparse

from sqlalchemy.orm import sessionmaker

from blockchain.blockexplorer import get_latest_block

from .coinsecrets import get_block_range, get_blocks
from .models import engine, Nulldata, FilteredNulldata


CONFIRMATIONS_NEEDED = 6



class Filterer:

    def __init__(self):
        self.Session = sessionmaker(bind=engine)
        self.session = self.Session()
        self.session.add()

    def run(self):
        pass



if __name__ == "__main__":
    f = Filterer()
    f.run()
