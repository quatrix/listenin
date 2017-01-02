from __future__ import print_function
from tornado.web import Application
from tornado.websocket import WebSocketHandler
from tornado.tcpserver import TCPServer
from tornado.iostream import StreamClosedError
from tornado.ioloop import IOLoop
from tornado.gen import coroutine
from collections import defaultdict
import jwt
import click
import json
import time
import copy


class BoxState(object):
    BLINK = 'INFO:root:blink'
    COLOR_CHANGE = 'INFO:root:setting led color to'
    FIFTY_HZ = 'RuntimeError: sample is 50hz hum'
    SUCCESS = 'INFO:root:sample recorded and uploaded'
    TOO_SHORT = 'RuntimeError: sample duration too short'

    def __init__(self, clients):
        self._clients = clients
        self._boxes = defaultdict(dict)

    def set_box_attr(self, box, key, value):
        _current_state = copy.deepcopy(self._boxes)

        v = {
            'time': int(time.time() / 10) * 10,
            'value': value,
        }

        _current_state[box][key] = v

        if self._boxes != _current_state:
            self._boxes = _current_state
            self.dispatch_to_websockets(box)

    def get_box_state(self, box):
        return json.dumps(self._boxes[box])

    def dispatch_to_websockets(self, box):
        if not self._clients[box]:
            return

        box_state = self.get_box_state(box)

        for c in self._clients[box]:
            c.write_message(box_state)

    def process_event(self, event):
        box = event['host'].split('listenin-')[-1]
        msg = event['message']

        print(event['@timestamp'], box, msg)
        if msg.startswith(self.COLOR_CHANGE):
            self.set_box_attr(box, 'color', msg.split()[-1])

        if msg.startswith(self.BLINK): 
            self.set_box_attr(box, 'blink', 'blink')

        if msg.startswith(self.FIFTY_HZ): 
            self.set_box_attr(box, 'status', 'Detected 50HZ Humm, check mixer connection.')

        if msg.startswith(self.TOO_SHORT): 
            self.set_box_attr(box, 'status', 'Detected Silence, check mixer connection.')

        if msg.startswith(self.SUCCESS): 
            self.set_box_attr(box, 'status', 'Last recording and upload successful.')


class BoxLogListener(TCPServer):
    """
    Gets logs from logstash and caches
    the latest state changes for each box
    """
    
    def set_event_handler(self, event_handler):
        self._event_handler = event_handler

    @coroutine
    def handle_stream(self, stream, address):
        try:
            while True:
                line = yield stream.read_until(b'\n')
                event = json.loads(line.decode('utf-8').strip())
                self._event_handler(event)
        except StreamClosedError:
            pass


class SocketHandler(WebSocketHandler):
    def check_origin(self, origin):
        return True

    def open(self):
        secret = self.settings['jwt_secret']
        token = self.get_argument('token')
        token = jwt.decode(token, secret, algorithms=['HS256'])
        club_id = token['club_id']

        self._box_id = self.settings['clubs'][club_id]['box_id']
        clients = self.settings['clients'][self._box_id]

        if self not in clients:
            clients.append(self)

        self.write_message(self.settings['boxes'].get_box_state(self._box_id))

    def on_close(self):
        clients = self.settings['clients'][self._box_id]

        if self in clients:
            clients.remove(self)

@click.command()
@click.option('--jwt-secret', required=True, help='Json Web Token secret')
@click.option('--clubs-file', required=True, help='Clubs json location')
@click.option('--ws-port', default=9998, help='WebSocket listen port')
@click.option('--log-port', default=9999, help='TCP port on which to listen to logs')
def main(jwt_secret, clubs_file, ws_port, log_port):
    clients = defaultdict(list)
    boxes = BoxState(clients)
    clubs = json.loads(open(clubs_file).read())

    box_log_listener = BoxLogListener()
    box_log_listener.set_event_handler(boxes.process_event)

    app = Application([
        (r'/updates/', SocketHandler),
    ], boxes=boxes, clients=clients, jwt_secret=jwt_secret, clubs=clubs)

    box_log_listener.listen(log_port)
    app.listen(ws_port)
    
    IOLoop.current().start()

if __name__ == '__main__':
    main()
