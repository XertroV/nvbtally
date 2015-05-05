from wsgiref.simple_server import make_server
from pyramid.config import Configurator
from pyramid.response import Response

from nvbtally.models import engine


def index_view(request):
    return {}


def main(global_config, **settings):
    config = Configurator()
    config.include('pyramid_chameleon')

    config.add_route('index', '/')
    config.add_view(index_view, route_name='index', renderer='index.pt')

    config.add_static_view(name='static', path='nvbtally:static')

    app = config.make_wsgi_app()
    return app
