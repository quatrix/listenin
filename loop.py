from __future__ import division

import click
import time
import subprocess
import logging
import sys
import requests
from threading import Thread, Event
from Queue import Queue, Empty
from led import LED


logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)


class ListenIn(object):
    def __init__(self, boxid, duration, interval, retrytime):
        self.boxid = boxid
        self.duration = duration
        self.interval = interval
        self.retrytime = retrytime

        self.led = LED(red=13, green=19, blue=26, initial_color='white')
        self._q = Queue()
        self.default_blink_interval = (5, 300)
        self.fast_blinking = (0.5, 500)


    def start_blinker(self):
        self._blinker_stop = Event()
        self._blinker_thread = Thread(target=self.blink_periodically)
        self._blinker_thread.start()

    def stop_blinker(self):
        self._blinker_stop.set()
        self._blinker_thread.join()

    def blink_periodically(self):
        last_blink_time = time.time()
        interval, duration = self.default_blink_interval

        while True:
            if self._blinker_stop.isSet():
                break

            try:
                interval, duration = self._q.get_nowait()
            except Empty:
                pass

            if time.time() - last_blink_time > interval:
                self.led.blink(duration=duration)
                last_blink_time = time.time()

            time.sleep(0.1)

    def listen(self):
        self.start_blinker()

        while True:
            t0 = time.time()

            try:
                self.led.set('red')
                sample = self.record_sample()
                self.led.set('blue')
                self.upload_sample(sample)
            except Exception:
                logging.exception('exception while recording and uploading')
                self.led.set('orange')
                self._q.put(self.fast_blinking)
                time.sleep(self.retrytime)
                self._q.put(self.default_blink_interval)
            else:
                logging.info('sample recorded and uploaded, sleeping for %d seconds', self.interval)
                self.led.set('green')

                sleep_time = self.interval - (time.time() - t0)
                if sleep_time >= 0:
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
            stdin=arecord_process.stdout,
            stdout=subprocess.PIPE,
        )

        arecord_process.stdout.close()

        sample = lame_process.communicate()[0]

        for p in arecord_process, lame_process:
            rc = p.wait()
            logging.info('%r process returned: %d', p, rc)


            if rc != 0:
                raise RuntimeError('failed to record: %r', rc)

        return sample

    def upload_sample(self, sample):
        url = 'http://mimosabox.com:55669/upload/{}/'.format(self.boxid)
        requests.post(url, data=sample)

    def cleanup(self):
        self.stop_blinker()

@click.command()
@click.option('--boxid', required=True, help='Unique id for box')
@click.option('--duration', default=30, help='Duration of each sample')
@click.option('--interval', default=300, help='How often to take a sample')
@click.option('--retrytime', default=10, help='How much seconds to wait before retrying on failure')
def main(boxid, duration, interval, retrytime):
    l = ListenIn(boxid, duration, interval, retrytime)
    
    try:
        l.listen()
    finally:
        print('cleanup')
        l.cleanup()

if __name__ == '__main__':
    main()
