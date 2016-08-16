import time
import os
import logging
import json
from tempfile import NamedTemporaryFile

from tornado.gen import coroutine, Return
from tornado.process import Subprocess
from base_handler import BaseHandler
from utils import normalize_acrcloud_response, is_same_song, normalize_metadata
from concurrent.futures import ThreadPoolExecutor


class IgnoreSample(Exception):
    pass


def is_recognized(sample):
    """
    Determines if sample is recognized by music fingerprinting
    """

    if sample is None:
        return False

    return sample['metadata'] is not None and 'recognized_song' in sample['metadata']


class UploadHandler(BaseHandler):
    _thread_pool = ThreadPoolExecutor(4)

    @coroutine
    def _recognize_sample_with_acrcloud(self, sample_path):
        recognizer = self.settings['recognizer'].recognize_by_file
        res = yield self._thread_pool.submit(recognizer, sample_path, 0)
        res = json.loads(res)

        if 'metadata' not in res:
            raise Return(None)

        raise Return(res['metadata']['music'][0])

    @coroutine
    def recognize_sample_with_acrcloud(self, sample_path):
        recognized_song = yield self._recognize_sample_with_acrcloud(sample_path)

        if recognized_song:
            self.extra_log_args['acrcloud'] = normalize_acrcloud_response(recognized_song)
            raise Return(recognized_song)

    @coroutine
    def _recognize_sample_with_gracenote(self, sample_path):
        conf = self.settings['gn_config']
        proc = Subprocess([
            'tools/gracetune_identify.py',
            '--client-id', conf['client_id'],
            '--user-id', conf['user_id'],
            '--license', conf['license'],
            '--filename', sample_path
            ], stdout=Subprocess.STREAM)

        yield proc.wait_for_exit()
        ret = yield proc.stdout.read_until_close()
        raise Return(json.loads(ret))

    @coroutine
    def recognize_sample_with_gracenote(self, sample_path):
        recognized_song = yield self._recognize_sample_with_gracenote(sample_path)

        if 'error' in recognized_song:
            logging.getLogger('logstash-logger').error('gracenote: %s', recognized_song['error'])
            return

        self.extra_log_args['gracenote'] = recognized_song
        raise Return(recognized_song)

    @coroutine
    def get_metadata(self, sample_path):
        metadata = {}

        try:
            metadata['gracenote'] = yield self.recognize_sample_with_gracenote(sample_path)

            if not metadata['gracenote']:
                metadata['acrcloud'] = yield self.recognize_sample_with_acrcloud(sample_path)

        except Exception:
            logging.getLogger('logstash-logger').exception('recognize_sample')

        metadata = {k: v for k, v in metadata.iteritems() if v is not None}

        raise Return(metadata)

    def is_fresh(self, sample):
        """
        Checks if sample is fresh by comparing seconds since its creation to the sample
        interval specified in settings
        """

        if sample is None:
            return False

        return (int(time.time()) - sample['_created']) < self.settings['sample_interval']

    def is_latest_sample_fresh_and_recognized(self, latest_sample):
        """
        Checks if latest sample fresh and recognized.
        """

        if self.is_fresh(latest_sample) and is_recognized(latest_sample):
            msg = 'latest sample is fresh and recognized'
            logging.getLogger('logstash-logger').info(msg)

            return True

    def is_same_song(self, latest_sample, metadata):
        """
        Checks if current sample is a duplicate of latest sample 
        """

        if is_recognized(latest_sample) and 'recognized_song' in metadata:
            latest_song = latest_sample['metadata']['recognized_song']
            current_song = metadata['recognized_song']

            if is_same_song(latest_song, current_song):
                msg = 'ignoring current sample as it is recognized as the latest sample'
                logging.getLogger('logstash-logger').info(msg)
                return True

    def should_replace_latest_with_current(self, latest_sample, metadata):
        """
        Should replace latest with current if latest sample is stale
        or if it's fresh and unrecognized, amd current sample is recognized
        """

        if not self.is_fresh(latest_sample):
            return

        if not is_recognized(latest_sample) and 'recognized_song' in metadata:
            return True

    def is_latest_sample_fresh_and_current_unrecognized(self, latest_sample, metadata):
        """
        Checks if latest sample still fresh for replacing, and that current sample is recognized
        """

        if self.is_fresh(latest_sample) and 'recognized_song' not in metadata:
            msg = 'latest sample still fresh and current sample unrecognized, ignoring'
            logging.getLogger('logstash-logger').info(msg)

            return True
        
    @coroutine
    def post(self, boxid):
        """
        FRESH sample: a sample younger than sampling interval (i.e if we want to sample every
        4 minutes, then a sample taken < 4 minutes ago considered fresh, otherwise it's STALE)

        1. If latest sample is FRESH and it's recognized, ignore current sample.
        2. If latest sample recognized and current sample recognized,
           and they are the same song, ignore current sample.
        3. if lastest sample is STALE, use current sample.
        4. If latest sample is FRESH but not recognized:
          4.1. If current sample recognized, it replaces the last sample
          4.2. if current sample isn't recognized, ignore current sample
        """

        samples_dir = os.path.join(self.settings['samples_root'], boxid)
        sample_id = int(time.time())
        sample_path = os.path.join(samples_dir, '{}.mp3'.format(sample_id))
        metadata_path = os.path.join(samples_dir, '{}.json'.format(sample_id))
        latest_sample = self.settings['samples'].latest(boxid)

        self.extra_log_args = {
            'boxid': boxid,
            'sample_path': sample_path
        }

        if not os.path.isdir(samples_dir):
            os.mkdir(samples_dir)

        if self.is_latest_sample_fresh_and_recognized(latest_sample):
            return

        with NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
            tmp_file.write(self.request.body)
            tmp_file.flush()

            full_metadata = yield self.get_metadata(tmp_file.name)
            metadata = normalize_metadata(full_metadata)

            if self.is_same_song(latest_sample, metadata):
                return

            if self.is_latest_sample_fresh_and_current_unrecognized(latest_sample, metadata):
                return

            replace_latest = self.should_replace_latest_with_current(latest_sample, metadata)

            os.chmod(tmp_file.name, 0644)
            os.rename(tmp_file.name, sample_path)
            open(metadata_path, 'w').write(json.dumps(full_metadata))

            if replace_latest:
                msg = 'latest sample still fresh but unrecognized, replacing with recognized'
                logging.getLogger('logstash-logger').info(msg)
                self.settings['samples'].replace_latest(sample_id, boxid)
            else:
                logging.getLogger('logstash-logger').info('adding new sample')
                self.settings['samples'].add(sample_id, boxid)
