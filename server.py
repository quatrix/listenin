from tornado.web import Application, RequestHandler
from tornado.ioloop import IOLoop
from tornado.log import enable_pretty_logging
from tornado.options import parse_command_line, define, options
import logging
import os
import click
import time


class UploadHandler(RequestHandler):
    def post(self, boxid):
        samples_dir = os.path.join(self.settings['samples_root'], boxid)
        sample_path = os.path.join(samples_dir, '{}.mp3'.format(int(time.time())))
        logging.info('sample from boxid: %s -> %s', boxid, sample_path)

        if not os.path.isdir(samples_dir):
            os.mkdir(samples_dir)

        with open(sample_path, 'wb+') as f:
            f.write(self.request.body)

@click.command()
@click.option('--port', default=55669, help='Port to listen on')
@click.option('--samples-root', default='/usr/share/nginx/html/listenin/uploads', help='Where files go')
def main(port, samples_root):
    app = Application([
        (r"/upload/(.+)/", UploadHandler),
    ], debug=True, samples_root=samples_root)

    enable_pretty_logging()

    app.listen(port)
    IOLoop.current().start()

if __name__ == "__main__":
    main()
