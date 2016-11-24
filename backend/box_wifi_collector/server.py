from __future__ import print_function
from tornado.web import Application, RequestHandler
from tornado.ioloop import IOLoop
from tornado.gen import coroutine
from tornado.httpclient import AsyncHTTPClient
import click
import json
import math
from collections import namedtuple, Counter


_attrs = ['mac', 'first_seen', 'last_seen', 'power', 'packets', 'bssid', 'probed_essids']
Station = namedtuple('Station', _attrs)

WIFI_FREQ = 2412

class DISTANCE(object):
    UNKNOWN = 'UNKNOWN'
    VERY_CLOSE = "VERY_CLOSE"
    CLOSE = "CLOSE"
    FAR = "FAR"
    VERY_FAR= "VERY_FAR"


def db_to_distance(db):
    """
    FSPL function taken from
    http://stackoverflow.com/questions/11217674/how-to-calculate-distance-from-wifi-router-using-signal-strength
    """

    return int(math.pow(10, (27.55 - (20 * math.log10(WIFI_FREQ)) + abs(db)) / 20.0))


def distance_classifer(db):
    distance = db_to_distance(db) 

    if distance < 3:
        return DISTANCE.VERY_CLOSE

    if distance < 10:
        return DISTANCE.CLOSE

    if distance < 30:
        return DISTANCE.FAR

    return DISTANCE.VERY_FAR




class WifiCollector(RequestHandler):
    @coroutine
    def record(self, host, distribution):
        body = '\n'.join([
            'wifi_clients_{},host={} value={}'.format(k, host, v)
            for k,v in distribution.iteritems()
        ])

        res = yield self.settings['http_client'].fetch(
            'http://localhost:8086/write?db={}'.format(self.settings['influx_db']),
            method='POST', 
            body=body
        )

        print(res)
        #curl -i -XPOST 'http://listenin.io:8086/write?db=listenin' -u box:box666kgb --data-binary "$BODY"
        
    @coroutine
    def post(self, box):
        stations = json.loads(self.request.body)
        stations = [Station(*s) for s in stations]

        distance_distribution = Counter([distance_classifer(s.power) for s in stations])
        yield self.record(box, distance_distribution)

@click.command()
@click.option('--port', default=5152, help='port to bind to')
@click.option('--influx-db-name', required=True, help='name of influx db')
def main(port, influx_db_name):
    http_client = AsyncHTTPClient()

    app = Application([
        (r'/wifis/(.+)/', WifiCollector),
    ], http_client=http_client, influx_db=influx_db_name)

    app.listen(port)
    IOLoop.current().start()

if __name__ == '__main__':
    main()
