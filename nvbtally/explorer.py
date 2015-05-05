from pycoin.encoding import b2a_base58

from wsgiref.simple_server import make_server
from pyramid.config import Configurator
from pyramid.response import Response

from sqlalchemy.orm import sessionmaker

from .models import engine, NetworkSettings, Resolution, Vote, ValidVoter

Session = sessionmaker(bind=engine)


def _all_b_to_str(l):
    return list(map(lambda i: str(i), l))


def index_view(request):
    return {}


def info_json(request):
    session = Session()
    ns = session.query(NetworkSettings).first()
    return {
        'Admin ID': str(ns.admin_address),
        'Network Name': str(ns.network_name),
    }


def resolutions_json(request):
    session = Session()
    rs = session.query(Resolution).all()
    rs_unresolved = list(map(lambda r: [str(r.res_name), str(r.url), r.end_timestamp], filter(lambda r: r.resolved == 0, rs)))
    rs_resolved = list(map(lambda r: [str(r.res_name), str(r.url), r.votes_for // 255, r.votes_total // 255], filter(lambda r: r.resolved == 1, rs)))
    return {
        'unfinalized': rs_unresolved,
        'finalized': rs_resolved,
    }


def main(global_config, **settings):
    config = Configurator()
    config.include('pyramid_chameleon')

    config.add_route('index', '/')
    config.add_view(index_view, route_name='index', renderer='index.pt')
    config.add_route('info', '/info')
    config.add_view(info_json, route_name='info', renderer='json')

    config.add_route('resolutions', '/resolutions')
    config.add_view(resolutions_json, route_name='resolutions', renderer='json')


    config.add_static_view(name='static', path='nvbtally:static')

    app = config.make_wsgi_app()
    return app
