from __future__ import division

import click
import time
import subprocess
import logging
import sys
import requests
from led import LED


logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)


class ListenIn(object):
    def __init__(self, boxid, duration, interval, retrytime):
        self.boxid = boxid
        self.duration = duration
        self.interval = interval
        self.retrytime = retrytime

        self.led = LED(red=13, green=19, blue=26)
        self.led.set('white')

    def listen(self):
        while True:
            t0 = time.time()
            self.led.blink()

            try:
                self.upload_sample(self.record_sample())
            except Exception:
                logging.exception('exception while recording and uploading')
                self.led.set('red')
                time.sleep(self.retrytime)
            else:
                logging.info('sample recorded and uploaded, sleeping for %d seconds', self.interval)
                self.led.set('green')

                sleep_time = self.interval - (time.time() - t0)
                if sleep_time >= 0;
                    time.sleep(sleep_time)
        
    def record_sample(self):
        arecord_args = 'arecord -D plughw:1,0 -f cd -t raw -d {}'.format(self.duration)
        lame_args = 'lame -r -h -V 0 - -'

        logging.debug(arecord_args)

        arecord_process = subprocess.Popen(
            arecord_args.split(),
            stdout=subprocess.PIPE,
        )

        lame_process = subprocess.Popen(
            lame_args.split(),
            stdin=arecord_process.stdout
        )

        arecord_process.stdout.close()

        sample = lame_process.communicate()[0]

        for p in arecord_process, lame_process:
            logging.info('%r process returned: %d', p, p.returncode)

            if p.returncode != 0:
                raise RuntimeError('failed to record: %r', rc)

        return sample

    def upload_sample(self, sample):
        url = 'http://mimosabox.com:55669/upload/{}/'.format(self.boxid)
        requests.post(url, data=sample)


@click.command()
@click.option('--boxid', required=True, help='Unique id for box')
@click.option('--duration', default=30, help='Duration of each sample')
@click.option('--interval', default=300, help='How often to take a sample')
@click.option('--retrytime', default=10, help='How much seconds to wait before retrying on failure')
def main(boxid, duration, interval, retrytime):
    ListenIn(boxid, duration, interval, retrytime).listen()

if __name__ == '__main__':
    main()
