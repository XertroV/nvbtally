#!/usr/bin/env/python3
__author__ = 'xertrov'

# run like:
# $ python -m nvbtally.updater -h

from queue import Queue
from time import sleep, time
import argparse

from sqlalchemy.orm import sessionmaker

from blockchain.blockexplorer import get_latest_block

from .coinsecrets import get_block_range, get_blocks

from .models import engine, Nulldata, ScannedBlock

CONFIRMATIONS_NEEDED = 1


class Updater:

    def __init__(self):
        self.Session = sessionmaker(bind=engine)
        self.session = self.Session()
        self.session.add(ScannedBlock(height=0))

    def run(self, starting_block=350000, run_forever=False, sleep_for=30):
        q = Queue()

        top_block = get_latest_block().height - CONFIRMATIONS_NEEDED
        min_block = starting_block

        cached_blocks = set()

        def update_queue():
            nonlocal cached_blocks
            _chunk = 750  # 1000 throws exception
            for i in range(min_block, top_block + 1, _chunk):
                comp_range = list(filter(lambda j: j not in cached_blocks, range(i, i + _chunk)))
                cached_blocks = cached_blocks | {i.height for i in self.session.query(ScannedBlock).filter(ScannedBlock.height.in_(comp_range)).all()}
            for i in range(min_block, top_block + 1):
                if i not in cached_blocks:
                    q.put(i)
                    cached_blocks.add(i)

        update_queue()

        while True:
            n = min(q.qsize(), 50)

            if n == 0:
                if run_forever:
                    print(int(time()), 'No blocks with >= %d confirmations, sleeping for %d seconds then updating...' % (CONFIRMATIONS_NEEDED, sleep_for))
                    sleep(sleep_for)
                    top_block = get_latest_block().height - CONFIRMATIONS_NEEDED
                    update_queue()
                    continue
                else:
                    break

            to_fetch = [q.get() for _ in range(n)]
            print('Fetching %d, min: %d, max: %d' % (n, min(to_fetch), max(to_fetch)))
            blocks = get_blocks(*to_fetch)

            for block in blocks:
                h = block['height']
                t = block['timestamp']
                nds = block['op_returns']
                self.session.add_all([Nulldata(height=h, timestamp=t, txid=nulldata['txid'], script=nulldata['script']) for nulldata in nds])
                self.session.add(ScannedBlock(height=h))
                self.session.commit()
                print('Processed', block['height'])


parser = argparse.ArgumentParser(description="Update DB with new OP_RETURN txs.")
parser.add_argument('--watch', help='Remain open and wait for new blocks.', action='store_true')
parser.add_argument('--sleepfor', help='Seconds to sleep after update routine', type=int, default=30)
args = parser.parse_args()

if __name__ == "__main__":
    u = Updater()
    u.run(350000, args.watch, args.sleepfor)
