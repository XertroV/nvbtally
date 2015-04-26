__author__ = 'xertrov'

# run like:
# $ python -m nvbtally.updater

from queue import Queue
from time import sleep, time

from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from blockchain.blockexplorer import get_latest_block

from .coinsecrets import get_block_range, get_blocks


engine = create_engine('sqlite:///temp.sqlite', echo=True)
Base = declarative_base()

CONFIRMATIONS_NEEDED = 6

class Vote(Base):
    __tablename__ = 'votes'

    id = Column(Integer, primary_key=True)
    txid = Column(String)
    timestamp = Column(Integer)
    script = Column(String)
    address = Column(String)


class Nulldata(Base):
    __tablename__ = 'nulldatas'

    id = Column(Integer, primary_key=True)
    height = Column(Integer)
    timestamp = Column(Integer)
    txid = Column(String)
    script = Column(String)
    address = Column(String, default='')

    def __repr__(self):
        return "<Nulldata(txid=%s, script=%s, address=%s)>" % (self.txid, self.script, self.address)

class ScannedBlock(Base):
    __tablename__ = 'scanned_blocks'

    id = Column(Integer, primary_key=True)
    height = Column(Integer)


Base.metadata.create_all(engine)


class Updater:

    def __init__(self):
        self.Session = sessionmaker(bind=engine)
        self.session = self.Session()
        self.session.add(ScannedBlock(height=0))

    def update(self, starting_block, run_forever=False):
        q = Queue()

        top_block = get_latest_block().height - CONFIRMATIONS_NEEDED
        min_block = starting_block

        def update_queue():
            exclude_blocks = []
            _chunk = 10
            for i in range(min_block, top_block + 1, _chunk):
                exclude_blocks.extend(self.session.query(ScannedBlock).filter(ScannedBlock.height.in_(range(i, i + _chunk))).all())
            exclude_heights = set([b.height for b in exclude_blocks])
            for i in range(min_block, top_block + 1):
                if i not in exclude_heights:
                    q.put(i)

        update_queue()

        while True:
            n = min(q.qsize(), 50)
            sleep_for = 30

            if n == 0:
                if run_forever:
                    print(int(time()), 'No blocks with >= 6 confirmations, sleeping for %d seconds then updating...' % sleep_for)
                    sleep(sleep_for)
                    top_block = get_latest_block().height - 6
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

if __name__ == "__main__":
    u = Updater()
    u.update(350000, False)
