from __future__ import print_function
from tornado.web import Application, RequestHandler
from tornado.ioloop import IOLoop
from tornado.gen import coroutine
from tornado.httpclient import AsyncHTTPClient
from operator import attrgetter
import click
import json
import math
import time
import jwt
from collections import namedtuple, Counter


_attrs = ['mac', 'first_seen', 'last_seen', 'power', 'packets', 'bssid', 'probed_essids']
Station = namedtuple('Station', _attrs)


def group_series(series):
    s = Counter([int(math.ceil(x/10)*10) for x in series])

    for i in range(-90, 10, 10):
        if i not in s:
            s[i] = 0

    return s



class WifiCollector(RequestHandler):
    def get_token(self):
        secret = self.settings['jwt_secret']
        token = self.get_argument('token') 
        return jwt.decode(token, secret, algorithms=['HS256'])

    def get_club_id(self):
        return self.get_token()['club_id']

    @coroutine
    def record(self, host, distribution):
        body = '\n'.join([
            'wifi_clients_{},host={} value={}'.format(k, host, v)
            for k,v in distribution.iteritems()
        ])
        print(body)

        res = yield self.settings['http_client'].fetch(
            'http://localhost:8086/write?db={}'.format(self.settings['influx_db']),
            method='POST', 
            body=body
        )

        print(res)
        
    @coroutine
    def post(self):
        box = self.get_club_id()

        stations = json.loads(self.request.body)
        stations = [Station(*s) for s in stations]

        distance_distribution = group_series(map(attrgetter('power'), stations))
        distance_distribution['total'] = len(stations)

        yield self.record(box, distance_distribution)

@click.command()
@click.option('--port', default=5152, help='Port to bind to')
@click.option('--influx-db-name', required=True, help='Name of influx db')
@click.option('--secret', required=True, help='JWT Secret')
def main(port, influx_db_name, secret):
    http_client = AsyncHTTPClient()

    app = Application([
        (r'/wifis', WifiCollector),
    ], http_client=http_client, influx_db=influx_db_name, secret=secret)

    app.listen(port)
    IOLoop.current().start()

if __name__ == '__main__':
    main()
