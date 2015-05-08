from pycoin.encoding import b2a_base58

from wsgiref.simple_server import make_server
from pyramid.config import Configurator
from pyramid.response import Response

from sqlalchemy.orm import sessionmaker
from sqlalchemy import func, and_

from .models import engine, NetworkSettings, Resolution, Vote, ValidVoter, Nulldata, Delegate

Session = sessionmaker(bind=engine)


def _all_b_to_str(l):
    return list(map(lambda i: str(i), l))


def give_session(f):
    def inner(request):
        s = Session()
        r = f(request, s)
        s.close()
        return r
    return inner


def index_view(request):
    return {}


@give_session
def info_json(request, session):
    ns = session.query(NetworkSettings).first()
    max_height = session.query(func.max(Nulldata.height)).one()[0]
    num_vote_actions = session.query(func.count(Vote.nulldata_id)).one()[0]
    num_voters = session.query(func.count(ValidVoter.id)).one()[0]

    return {
        'Admin ID': str(ns.admin_address),
        'Network Name': str(ns.network_name),
        'Chain Height (with confirmations)': max_height,
        'Number of Vote Actions': num_vote_actions,
        'Number of Voters': num_voters,
    }


@give_session
def resolutions_json(request, session):
    rs = session.query(Resolution).all()
    rs_unresolved = list(map(lambda r: {'name': r.res_name.decode(), 'url': r.url.decode(), 'predicted_for': r.votes_for / 255, 'predicted_total': r.votes_total / 255, 'end': r.end_timestamp}, filter(lambda r: r.resolved == 0, rs)))
    rs_resolved = list(map(lambda r: {'name': r.res_name.decode(), 'url': r.url.decode(), 'votes_for': r.votes_for / 255, 'votes_total': r.votes_total / 255, 'end': r.end_timestamp}, filter(lambda r: r.resolved == 1, rs)))
    return {
        'unfinalized': rs_unresolved,
        'finalized': rs_resolved,
    }


@give_session
def voters_json(request, session):
    vs = session.query(ValidVoter).all()
    return {'voters': list(map(lambda v: {'address': v.address, 'empowerment': v.votes_empowered}, vs))}


@give_session
def voter_detail_json(request, session):
    voter = session.query(ValidVoter).filter(ValidVoter.address == request.json_body['address']).one()
    delegate_map = session.query(Delegate).filter(Delegate.voter_id == voter.id).first()
    delegate_addr = None if delegate_map is None else session.query(ValidVoter).filter(ValidVoter.id == delegate_map.delegate_id).one().address
    votes = session.query(Vote).filter(Vote.address == voter.address).all()
    return {
        'voter': {'delegate': delegate_addr, 'empowerment': voter.votes_empowered, 'num_votes': len(votes), 'address': voter.address},
        'votes': [{'res_name': v.res_name.decode(), 'superseded': v.superseded, 'vote_num': v.vote_num / 255, 'txid': v.nulldata.txid} for v in votes]
    }


@give_session
def votes_json(request, session):
    rs = filter(lambda v: v.superseded == False, session.query(Vote).all())
    return {'votes': list(map(lambda v: {'res_name': v.res_name.decode(), 'address': v.address, 'txid': v.nulldata.txid, 'vote_num': v.vote_num, 'vote_superseded': v.superseded}, rs))}


@give_session
def res_detail_json(request, session):
    res = session.query(Resolution).filter(Resolution.res_name == request.json_body['res_name'].encode()).one()
    vs = session.query(Vote).filter(Vote.res_name == res.res_name).filter(Vote.superseded == False).all()
    return {
        'resolution': {'categories': res.categories, 'url': res.url.decode(), 'end': res.end_timestamp, 'votes_for': res.votes_for / 255,
                       'votes_total': res.votes_total / 255, 'resolved': res.resolved, 'res_name': res.res_name.decode()},
        'votes': [{'address': v.address, 'txid': v.nulldata.txid, 'vote_num': v.vote_num} for v in vs],
    }


def main(global_config, **settings):
    config = Configurator()
    config.include('pyramid_chameleon')

    config.add_route('index', '/')
    config.add_view(index_view, route_name='index', renderer='templates/index.pt')
    config.add_route('info', '/info')
    config.add_view(info_json, route_name='info', renderer='json')

    config.add_route('resolutions', '/resolutions')
    config.add_view(resolutions_json, route_name='resolutions', renderer='json')

    config.add_route('voters', '/voters')
    config.add_view(voters_json, route_name='voters', renderer='json')

    config.add_route('voter_detail', '/voter_detail')
    config.add_view(voter_detail_json, route_name='voter_detail', renderer='json')

    config.add_route('votes', '/votes')
    config.add_view(votes_json, route_name='votes', renderer='json')

    config.add_route('res_detail', '/res_detail')
    config.add_view(res_detail_json, route_name='res_detail', renderer='json')

    config.add_static_view(name='static', path='nvbtally:static')

    app = config.make_wsgi_app()
    return app
