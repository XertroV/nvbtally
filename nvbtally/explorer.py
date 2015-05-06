from pycoin.encoding import b2a_base58

from wsgiref.simple_server import make_server
from pyramid.config import Configurator
from pyramid.response import Response

from sqlalchemy.orm import sessionmaker

from .models import engine, NetworkSettings, Resolution, Vote, ValidVoter

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
    return {
        'Admin ID': str(ns.admin_address),
        'Network Name': str(ns.network_name),
    }


@give_session
def resolutions_json(request, session):
    rs = session.query(Resolution).all()
    rs_unresolved = list(map(lambda r: [str(r.res_name), str(r.url), r.end_timestamp], filter(lambda r: r.resolved == 0, rs)))
    rs_resolved = list(map(lambda r: [str(r.res_name), str(r.url), r.votes_for // 255, r.votes_total // 255], filter(lambda r: r.resolved == 1, rs)))
    return {
        'unfinalized': rs_unresolved,
        'finalized': rs_resolved,
    }


@give_session
def voters_json(request, session):
    vs = session.query(ValidVoter).all()
    return {'voters': list(map(lambda v: (v.address, v.votes_empowered), vs))}


@give_session
def votes_json(request, session):
    rs = session.query(Vote).all()
    return {'votes': list(map(lambda v: {'res_name': v.res_name.decode(), 'address': v.address, 'txid': v.nulldata.txid, 'vote_num': v.vote_num}, rs))}


def main(global_config, **settings):
    config = Configurator()
    config.include('pyramid_chameleon')

    config.add_route('index', '/')
    config.add_view(index_view, route_name='index', renderer='index.pt')
    config.add_route('info', '/info')
    config.add_view(info_json, route_name='info', renderer='json')

    config.add_route('resolutions', '/resolutions')
    config.add_view(resolutions_json, route_name='resolutions', renderer='json')

    config.add_route('voters', '/voters')
    config.add_view(voters_json, route_name='voters', renderer='json')

    config.add_route('votes', '/votes')
    config.add_view(votes_json, route_name='votes', renderer='json')

    config.add_static_view(name='static', path='nvbtally:static')

    app = config.make_wsgi_app()
    return app
