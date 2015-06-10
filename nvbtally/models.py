__author__ = 'xertrov'

import logging

from sqlalchemy import create_engine, Column, String, Integer, ForeignKey, Boolean, Index
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

engine = create_engine('sqlite:///temp.sqlite', connect_args={'timeout': 15})#, echo=True)
Base = declarative_base()

#
# Updater
#


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


#
# filter_votes
#


class FilteredNulldata(Base):
    __tablename__ = 'filtered_nulldatas'

    id = Column(Integer, primary_key=True)
    nulldata_id = Column(Integer, ForeignKey('nulldatas.id'), unique=True)


class RawVote(Base):
    __tablename__ = 'raw_votes'

    id = Column(Integer, primary_key=True)
    nulldata_id = Column(Integer, ForeignKey('nulldatas.id'), unique=True)

    nulldata = relationship("Nulldata", uselist=False, backref='raw_vote')


#
# tally
#


class ProcessedVote(Base):
    __tablename__ = 'processed_votes'

    id = Column(Integer, primary_key=True)
    raw_vote_id = Column(Integer, ForeignKey('raw_votes.id'), unique=True)

    raw_vote = relationship("RawVote", uselist=False, backref='processed_vote')

    @property
    def script(self):
        return self.raw_vote.nulldata.script


class Vote(Base):
    __tablename__ = 'votes'

    vote_num = Column(Integer)
    res_name = Column(String, ForeignKey('resolutions.res_name'))
    nulldata_id = Column(Integer, ForeignKey('nulldatas.id'), primary_key=True)
    voter_id = Column(Integer, ForeignKey('valid_voters.id'))
    address = Column(String)
    height = Column(Integer)
    superseded = Column(Boolean, default=False)

    resolution = relationship('Resolution', uselist=False, backref='votes')
    nulldata = relationship('Nulldata', uselist=False, backref='vote')
    voter = relationship('ValidVoter', uselist=False, backref='vote')


class NetworkSettings(Base):
    __tablename__ = 'network_settings'

    id = Column(Integer, primary_key=True)
    admin_address = Column(String)
    network_name = Column(String)


class ValidVoter(Base):
    __tablename__ = 'valid_voters'

    id = Column(Integer, primary_key=True)
    address = Column(String, unique=True)
    votes_empowered = Column(Integer)


class Delegate(Base):
    __tablename__ = 'delegates'

    voter_id = Column(Integer, ForeignKey('valid_voters.id'), primary_key=True)
    delegate_id = Column(Integer, ForeignKey('valid_voters.id'))

    voter = relationship("ValidVoter", foreign_keys="Delegate.voter_id")
    delegate = relationship("ValidVoter", foreign_keys="Delegate.delegate_id")


class Resolution(Base):
    __tablename__ = 'resolutions'

    res_name = Column(String, primary_key=True)
    categories = Column(Integer)
    url = Column(String)
    end_timestamp = Column(Integer)
    votes_for = Column(Integer, default=0)
    votes_total = Column(Integer, default=0)
    resolved = Column(Integer, default=0)


class Transfers(Base):
    __tablename__ = 'transfers'

    voter_id = Column(Integer, ForeignKey('valid_voters.id'), primary_key=True)
    after_time = Column(Integer)
    new_address = Column(String)


class TransferEnabled(Base):
    __tablename__ = 'transfer_enabled'

    voter_id = Column(Integer, ForeignKey('valid_voters.id'), primary_key=True)
    transfer_enabled = Column(Boolean, default=False)


tally_tables = [ProcessedVote, NetworkSettings, Resolution, ValidVoter, Vote, Delegate, TransferEnabled, Transfers]

Base.metadata.create_all(engine)
