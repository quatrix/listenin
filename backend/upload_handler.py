import time
import os
import logging
import json
from tempfile import NamedTemporaryFile

from tornado.gen import coroutine, Return
from tornado.process import Subprocess
from base_handler import BaseHandler
from utils import normalize_acrcloud_response, is_same_song, get_metadata_from_json
from concurrent.futures import ThreadPoolExecutor


class UploadHandler(BaseHandler):
    _thread_pool = ThreadPoolExecutor(4)

    @coroutine
    def recognize_sample(self, sample_path):
        f = self.settings['recognizer'].recognize_by_file
        r = yield self._thread_pool.submit(f, sample_path, 0)
        r = json.loads(r)

        if 'metadata' not in r:
            raise Return(None)

        raise Return(r['metadata']['music'][0])

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
    def recognize_sample_with_acrcloud(self, sample_path):
        recognized_song = yield self.recognize_sample(sample_path)

        if recognized_song:
            self.extra_log_args['acrcloud'] = normalize_acrcloud_response(recognized_song)
            raise Return(recognized_song)

    @coroutine
    def write_metadata(self, sample_path, metadata_path):
        metadata = {}

        try:
            gracenote = yield self.recognize_sample_with_gracenote(sample_path)

            if gracenote:
                metadata['gracenote'] = gracenote
            else:
                acrcloud = yield self.recognize_sample_with_acrcloud(sample_path)
                if acrcloud:
                    metadata['recognized_song'] = acrcloud

        except Exception as e:
            logging.getLogger('logstash-logger').error('recognize_sample: %s', e)

        try:
            open(metadata_path, 'w').write(json.dumps(metadata))
        except Exception as e:
            logging.getLogger('logstash-logger').error('write metadata: %s', e)

    def is_fresh(self, sample):
        """
        Checks if sample is fresh by comparing seconds since its creation to the sample
        interval specified in settings
        """

        if sample is None:
            return False

        return (int(time.time()) - sample['_created']) < self.settings['sample_interval']

    def is_recognized(self, sample):
        """
        Determines if sample is recognized by music fingerprinting
        """

        if sample is None:
            return False

        return sample['metadata'] is not None and 'recognized_song' in sample['metadata']

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

        # if latest sample is fresh and recognized, ignore current sample
        if self.is_fresh(latest_sample) and self.is_recognized(latest_sample):
            msg = 'latest sample is fresh and recognized'
            logging.getLogger('logstash-logger').info(msg)
            return

        tmp_file = NamedTemporaryFile(delete=False, suffix='.mp3')
        tmp_metadata_file = tmp_file.name.replace('.mp3', '.json')
        tmp_file.write(self.request.body)
        tmp_file.flush()

        yield self.write_metadata(tmp_file.name, tmp_metadata_file)

        # get_metadata_from_json normalizes the json a bit
        # FIXME: this is just for sake of uniformaty, but actaully
        # write_metadata should instead return metadata
        # and metadata normalization should happen on metadata dict
        # not on json
        metadata = get_metadata_from_json(tmp_metadata_file)

        # nevermind the freshness of the latest sample, if current sample
        # is recognized and it's the same song as the latest sample, ignore current sample
        if self.is_recognized(latest_sample) and 'recognized_song' in metadata:
            latest_song = latest_sample['metadata']['recognized_song']
            current_song = metadata['recognized_song']

            if is_same_song(latest_song, current_song):
                msg = 'ignoring current sample as it is recognized as the latest sample'
                logging.getLogger('logstash-logger').info(msg)
                return

        replace_latest_with_current = False

        # if latest sample still fresh but not recognized, and the current
        # sample is recognized, we want to replace latest sample with current sample
        # otherwise, keep the latest sample and ignore current sample.
        if self.is_fresh(latest_sample) and not self.is_recognized(latest_sample):
            if 'recognized_song' in metadata:
                replace_latest_with_current = True
            else:
                msg = 'latest sample still fresh but both current sample and latest ' \
                      'sample are not recognized, ignoiring current sample'
                logging.getLogger('logstash-logger').info(msg)
                return

        os.chmod(tmp_file.name, 0644)
        os.rename(tmp_file.name, sample_path)
        os.rename(tmp_metadata_file, metadata_path)

        if replace_latest_with_current:
            msg = 'latest sample still fresh but unrecognized, replacing with recognized'
            logging.getLogger('logstash-logger').info(msg)
            self.settings['samples'].replace_latest(sample_id, boxid)
        else:
            logging.getLogger('logstash-logger').info('adding new sample')
            self.settings['samples'].add(sample_id, boxid)
