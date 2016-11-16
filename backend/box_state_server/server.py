from __future__ import print_function
from tornado.tcpserver import TCPServer
from tornado.iostream import StreamClosedError
from tornado.ioloop import IOLoop
from tornado.gen import coroutine


class BoxStateBuffer(TCPServer):
    """
    Gets logs from logstash and caches
    the latest state changes for each box
    """

    @coroutine
    def handle_stream(self, stream, address):
        try:
            while True:
                line = yield stream.read_until(b'\n')
                print(line.decode('utf-8').strip())
        except StreamClosedError:
            pass


def main():
    server = BoxStateBuffer()
    server.listen(9999)
    IOLoop.current().start()

if __name__ == '__main__':
    main()
