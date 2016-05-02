# -*- coding: utf-8 -*-

from tornado.web import Application, RequestHandler, stream_request_body
from tornado.ioloop import IOLoop
from tornado.log import enable_pretty_logging
from tornado.options import parse_command_line, define, options
from tornado.escape import json_decode
from ttldict import TTLDict
from collections import defaultdict
from datetime import datetime
from tempfile import NamedTemporaryFile

import subprocess
import logstash
import pytz
import logging
import os
import stat
import click
import time


def get_duration(f):
    r = subprocess.check_output(
        ['sox', f, '-n', 'stat'],
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )

    for l in r.split('\n'):
        if l.startswith('Length'):
            return float(l.split()[-1])


class BaseHandler(RequestHandler):
    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
        self.set_header("Access-Control-Allow-Headers", "Content-Type, Depth, User-Agent, X-File-Size, X-Requested-With, X-Requested-By, If-Modified-Since, X-File-Name, Cache-Control")

    def options(self, *args, **kwargs):
        self.finish()
            
    def on_finish(self):
        status_code = self.get_status()

        extra = {
            'device_id': self.request.headers.get('X-Device-Id'),
            'latlng': self.request.headers.get('X-LatLng'),
            'method': self.request.method,
            'uri': self.request.uri,
            'ip': self.request.remote_ip,
            'status_code': status_code,
            'request_time': 1000.0 * self.request.request_time(),
        }

        if hasattr(self, 'extra_log_args'):
            extra.update(self.extra_log_args)

        extra = {k: v for k, v in extra.items() if v is not None}

        logger = logging.getLogger('logstash-logger')

        if status_code >= 400:
            logger.error('error', extra=extra, exc_info=True)
        else:
            logger.info('success', extra=extra)

class UploadHandler(BaseHandler):
    def post(self, boxid):
        samples_dir = os.path.join(self.settings['samples_root'], boxid)
        sample_path = os.path.join(samples_dir, '{}.mp3'.format(int(time.time())))

        self.extra_log_args = {
            'boxid': boxid,
            'sample_path': sample_path
        }

        if not os.path.isdir(samples_dir):
            os.mkdir(samples_dir)

        with open(sample_path, 'wb+') as f:
            f.write(self.request.body)

        try:
            self.extra_log_args['sample_duration'] = get_duration(sample_path)
        except Exception:
            logging.getLogger('logstash-logger').exception('get_duration')


def number_part_of_sample(sample):
    return int(sample[:-4])


def unix_time_to_readable_date(t):
    tz = pytz.timezone('Asia/Jerusalem')
    return datetime.fromtimestamp(t, tz=tz).strftime('%Y-%m-%d %H:%M:%S')


def age(t):
    return int(time.time() - t)


class SpyHandler(BaseHandler):
    def post(self):
        self.extra_log_args = json_decode(self.request.body)


class ClubsHandler(BaseHandler):
    _samples = TTLDict(default_ttl=15)
    _clubs = {
        'radio': {
            'name': 'Radio EPGB',
            'details': 'A home for underground music',
            'address': '7 Shadal St. Tel Aviv',
            'phone': '03-5603636',
            'location': { 
                'lat': 32.06303301410757, 
                'lng': 34.775075912475586,
            },
        },
        'pasaz' : {
            'name': 'The Pasáž',
            'details': 'The Pasáž (the Passage)',
            'address': '94 Allenby St. Tel Aviv',
            'phone': '077-3323118',
            'location': { 
                'lat': 32.0663031,
                'lng': 34.7719147,
            },
        }
    }

    def _get_samples(self, club):
        path = os.path.join(self.settings['samples_root'], club)
        n_samples = self.settings['n_samples']
        time_now = time.time()

        samples = filter(
            lambda x: age(x) < self.settings['max_age'],
            map(number_part_of_sample, os.listdir(path))
        )

        return sorted(samples, reverse=True)[:n_samples]


    def _set_ttl(self, club):
        if not self._samples[club]:
            return

        sample_interval = self.settings['sample_interval']
        seconds_since_last_sample = age(self._samples[club][0])

        if seconds_since_last_sample > sample_interval:
            return

        self._samples.set_ttl(
            club,
            sample_interval - seconds_since_last_sample
        )
    
    def get_samples(self, club):
        if club in self._samples:
            return self._samples[club]

        self._samples[club] = self._get_samples(club)
        self._set_ttl(club)

        return self._samples[club]

    def enrich_samples(self, samples, club):
        return [{
            'date': unix_time_to_readable_date(sample),
            'link': '{}/uploads/{}/{}.mp3'.format(
                self.settings['base_url'],
                club,
                sample
            )
        } for sample in samples]

    def get_logo(self, club):
        sizes = 'hdpi', 'mdpi', 'xhdpi', 'xxhdpi','xxxhdpi'
        prefix = '{}/images/{}'.format(
            self.settings['base_url'],
            club
        )

        return {
            size: '{}/{}.png'.format(prefix, size)
            for size in sizes
        }

    def get(self):
        res = {}

        for club in os.listdir(self.settings['samples_root']):
            res[club] = self._clubs[club]
            res[club]['logo'] = self.get_logo(club)
            
            samples = self.get_samples(club)
            samples = self.enrich_samples(samples, club)
            res[club]['samples'] = samples
            
        self.finish(res)

@click.command()
@click.option('--port', default=55669, help='Port to listen on')
@click.option('--samples-root', default='/usr/share/nginx/html/listenin.io/uploads/', help='Where files go')
@click.option('--base-url', default='http://listenin.io/', help='Base URL')
@click.option('--n-samples', default=10, help='How many samples to return')
@click.option('--sample-interval', default=300, help='Sampling interval')
@click.option('--max-age', default=3600*2 , help='Oldest sample age')
def main(port, samples_root, base_url, n_samples, sample_interval, max_age):

    logstash_handler = logstash.LogstashHandler(
        'localhost',
        5959,
        version=1
    )

    logstash_logger = logging.getLogger('logstash-logger')
    logstash_logger.setLevel(logging.INFO)
    logstash_logger.addHandler(logstash_handler)

    app = Application([
        (r"/upload/(.+)/", UploadHandler),
        (r"/clubs", ClubsHandler),
        (r"/spy", SpyHandler),
    ], 
        debug=True,
        samples_root=samples_root,
        base_url=base_url,
        n_samples=n_samples,
        sample_interval=sample_interval,
        max_age=max_age,
    )

    enable_pretty_logging()

    app.listen(port, xheaders=True)
    IOLoop.current().start()

if __name__ == "__main__":
    main()
