from __future__ import division

import click
import time
import subprocess
import logging
import sys
import os
import requests
from threading import Thread, Event
from Queue import Queue, Empty
from led import LED
from wave_anylizer import Wave


logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)


def get_duration(f):
    r = subprocess.check_output(
        ['sox', f, '-n', 'stat'],
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )

    for l in r.split('\n'):
        if l.startswith('Length'):
            return float(l.split()[-1])


class ListenIn(object):
    def __init__(self, token, duration, interval, retrytime):
        self.token = token
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
            try:
                logging.info('waiting for audio signal')
                self.led.set('purple')
                r = self.record_sample()
                next(r)
                logging.info('recording')
                self.led.set('red')
                sample = next(r)
                self.led.set('blue')
                t0 = time.time()
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
        output_file = '/tmp/output.mp3'
        processed_file = '/tmp/processed.mp3'
        downsampled_output_file = '/tmp/downsampled.1c.8k.flac'

        for f in output_file, downsampled_output_file:
            if os.path.exists(f):
                os.unlink(f)

        rec_cmd = 'rec --no-show-progress -t mp3 -C 0 {} highpass 60 silence 1 0.1 -35d 1 2.0 -35d trim 0 {}'.format(
            output_file,
            self.duration,
        )

        rec_process = subprocess.Popen(rec_cmd.split())

        while True:
            rc = rec_process.poll()

            if rc is not None:
                break

            try:
                if os.path.getsize(output_file) > 0:
                    break
            except OSError:
                pass

            time.sleep(0.1)

        if rc is None:
            yield

        rc = rec_process.wait()

        if rc != 0:
            raise RuntimeError('failed to record: %r', rc)


        normalize_cmd = 'sox --norm {} {}'.format(output_file, processed_file)
        subprocess.check_call(normalize_cmd.split())

        downsample_cmd = 'sox {} -r 8000 -b 16 -c 1 {}'.format(processed_file, downsampled_output_file)
        subprocess.check_call(downsample_cmd.split())

        w = Wave(downsampled_output_file) 

        if w.length < self.duration:
            raise RuntimeError('sample duration too short ({}<{})'.format(w.length, self.duration))

        if w.is_silence:
            raise RuntimeError('sample is silent')

        if w.is_noise:
            raise RuntimeError('sample is 50hz hum')

        yield open(processed_file).read()

    def assert_sample_is_valid(self, sample_file):
        pass

    def upload_sample(self, sample):
        url = 'http://api.listenin.io/upload?token={}'.format(self.token)
        requests.post(url, data=sample, timeout=60).raise_for_status()

    def cleanup(self):
        self.stop_blinker()


@click.command()
@click.option('--token-file', default='/etc/listenin/token', help='Duration of each sample', type=click.Path())
@click.option('--duration', default=20, help='Duration of each sample')
@click.option('--interval', default=60, help='How often to take a sample')
@click.option('--retrytime', default=10, help='How much seconds to wait before retrying on failure')
def main(token_file, duration, interval, retrytime):
    token = open(token_file).read()

    l = ListenIn(token, duration, interval, retrytime)
    
    try:
        l.listen()
    finally:
        l.cleanup()

if __name__ == '__main__':
    main()
