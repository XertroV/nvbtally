__author__ = 'xertrov'

import json

import requests
from requests_futures.sessions import FuturesSession

def get_block_range(first, last):
    return get_blocks(*range(first, last + 1))

def get_blocks(*heights):
    urls = [get_block_coinsecrets_url(h) for h in heights]
    session = FuturesSession()
    reqs = [session.get(url) for url in urls]
    responses = [r.result() for r in reqs]
    resps_json = [json.loads(r.content.decode()) for r in responses]
    return resps_json

def get_block_coinsecrets_url(h):
    return 'http://api.coinsecrets.org/block/%d' % h