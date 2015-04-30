__author__ = 'xertrov'


from sqlalchemy import create_engine, Column, String, Integer, ForeignKey
from sqlalchemy.orm import sessionmaker, backref, relationship
from sqlalchemy.ext.declarative import declarative_base

engine = create_engine('sqlite:///temp.sqlite', echo=True)
Base = declarative_base()


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


class FilteredNulldata(Base):
    __tablename__ = 'filtered_nulldatas'

    id = Column(Integer, primary_key=True)
    nulldata_id = Column(Integer, ForeignKey('nulldatas.id'), unique=True)


class RawVote(Base):
    __tablename__ = 'raw_votes'

    id = Column(Integer, primary_key=True)
    nulldata_id = Column(Integer, ForeignKey('nulldatas.id'), unique=True)

    nulldata = relationship("Nulldata", uselist=False, backref='raw_vote')




Base.metadata.create_all(engine)