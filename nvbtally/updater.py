#!/usr/bin/env python3
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

CONFIRMATIONS_NEEDED = 2

class Updater:

    def __init__(self):
        self.Session = sessionmaker(bind=engine)
        self.session = self.Session()
        self.session.add(ScannedBlock(height=0))

    def strip_after(self, height):
        self.session.query(Nulldata).filter(Nulldata.height >= height).delete()
        self.session.query(ScannedBlock).filter(ScannedBlock.height >= height).delete()
        self.session.commit()

    def run(self, starting_block=351816, run_forever=False, sleep_for=30):
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
parser.add_argument('--strip-after', help='Remove all nulldatas from height H or up', type=int)
parser.add_argument('--start-from', help='Scan all nulldatas occuring in or after this block', type=int, default=351816)
args = parser.parse_args()

if __name__ == "__main__":
    u = Updater()
    if args.strip_after is not None:
        print('Stripped from %d onwards' % args.strip_after)
        u.strip_after(args.strip_after)
    else:
        u.run(args.start_from, args.watch, args.sleepfor)  # 351817 is the first NVB tx, so don't bother before this
