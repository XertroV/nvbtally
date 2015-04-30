__author__ = 'xertrov'


from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

engine = create_engine('sqlite:///temp.sqlite', echo=True)
Base = declarative_base()

Base.metadata.create_all(engine)

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


    def __repr__(self):
        return "<Nulldata(txid=%s, script=%s, address=%s)>" % (self.txid, self.script, self.address)

class FilteredNulldata(Base):
    __tablename__ = 'filtered_nulldatas'

    id = Column(Integer, primary_key=True)
    nulldataId = Column(Integer)


class Vote(Base):
    __tablename__ = 'votes'

    id = Column(Integer, primary_key=True)
    script = Column(String)
    txid = Column(String)
