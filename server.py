from tornado.web import Application, RequestHandler
from tornado.ioloop import IOLoop
from tornado.log import enable_pretty_logging
from tornado.options import parse_command_line, define, options
from ttldict import TTLDict
from collections import defaultdict
from datetime import datetime
import logging
import os
import click
import time


class BaseHandler(RequestHandler):
    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
        self.set_header("Access-Control-Allow-Headers", "Content-Type, Depth, User-Agent, X-File-Size, X-Requested-With, X-Requested-By, If-Modified-Since, X-File-Name, Cache-Control")

    def options(self, *args, **kwargs):
        self.finish()
            

class UploadHandler(BaseHandler):
    def post(self, boxid):
        samples_dir = os.path.join(self.settings['samples_root'], boxid)
        sample_path = os.path.join(samples_dir, '{}.mp3'.format(int(time.time())))
        logging.info('sample from boxid: %s -> %s', boxid, sample_path)

        if not os.path.isdir(samples_dir):
            os.mkdir(samples_dir)

        with open(sample_path, 'wb+') as f:
            f.write(self.request.body)


def number_part_of_sample(sample):
    return int(sample[:-4])


def unix_time_to_readable_date(t):
    return datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M:%S')


class ClubsHandler(BaseHandler):
    _samples = TTLDict(default_ttl=15)

    def _get_samples(self, club):
        path = os.path.join(self.settings['samples_root'], club)
        n_samples = self.settings['n_samples']
        samples = sorted(map(number_part_of_sample, os.listdir(path)), reverse=True)[:n_samples]

        return [{
            'date': unix_time_to_readable_date(sample),
            'age': int(time.time() - sample),
            'link': '{}/{}/{}.mp3'.format(self.settings['samples_url'], club, sample)
        } for sample in samples]

    def _set_ttl(self, club):
        if not self._samples[club]:
            return

        sample_interval = self.settings['sample_interval']
        seconds_since_last_sample = self._samples[club][0]['age']

        if seconds_since_last_sample > sample_interval:
            return

        self._samples.set_ttl(club, sample_interval - seconds_since_last_sample)
    
    def get_samples(self, club):
        if club in self._samples:
            return self._samples[club]

        self._samples[club] = self._get_samples(club)
        self._set_ttl(club)

        return self._samples[club]

    def get(self):
        res = defaultdict(dict)

        for club in os.listdir(self.settings['samples_root']):
            res[club]['samples'] = self.get_samples(club)
            
        self.finish(res)

@click.command()
@click.option('--port', default=55669, help='Port to listen on')
@click.option('--samples-root', default='/usr/share/nginx/html/listenin/uploads/', help='Where files go')
@click.option('--samples-url', default='http://mimosabox.com/listenin/uploads/', help='Samples base URL')
@click.option('--n-samples', default=10, help='How many samples to return')
@click.option('--sample-interval', default=300, help='Sampling interval')
def main(port, samples_root, samples_url, n_samples, sample_interval):
    app = Application([
        (r"/upload/(.+)/", UploadHandler),
        (r"/clubs", ClubsHandler),
    ], 
        debug=True,
        samples_root=samples_root,
        samples_url=samples_url,
        n_samples=n_samples,
        sample_interval=sample_interval,
    )

    enable_pretty_logging()

    app.listen(port)
    IOLoop.current().start()

if __name__ == "__main__":
    main()
