from base_handler import BaseHandler
import time
import os
import logging
import json
from tempfile import NamedTemporaryFile
from tornado.gen import coroutine, Return
from utils import normalize_acrcloud_response, get_bpm, get_duration
from concurrent.futures import ThreadPoolExecutor


class UploadHandler(BaseHandler):
    _thread_pool = ThreadPoolExecutor(4)

    @coroutine
    def recognize_sample(self, sample_path):
        f = self.settings['recognizer'].recognize_by_file
        r = yield self._thread_pool.submit(f, sample_path, 0)
        r = json.loads(r)

        if 'metadata' not in r:
            raise RuntimeError('unrecognized song')

        raise Return(r['metadata']['music'][0])

    @coroutine
    def write_metadata(self, sample_path, metadata_path):
        metadata = {}

        try:
            recognized_song = yield self.recognize_sample(sample_path)
            self.extra_log_args['acrcloud'] = normalize_acrcloud_response(recognized_song)
            metadata['recognized_song'] = recognized_song
        except Exception:
            logging.getLogger('logstash-logger').exception('recognize_sample')

        try:
            metadata['bpm'] = get_bpm(sample_path)
            self.extra_log_args['bpm'] = metadata['bpm']
        except Exception:
            logging.getLogger('logstash-logger').exception('get_bpm')

        try:
            metadata['duration'] = get_duration(sample_path)
            self.extra_log_args['sample_duration'] = get_duration(sample_path)
        except Exception:
            logging.getLogger('logstash-logger').exception('get_duration')

        if not metadata:
            return

        try:
            open(metadata_path, 'w').write(json.dumps(metadata))
        except Exception:
            logging.getLogger('logstash-logger').exception('write metadata')

    @coroutine
    def post(self, boxid):
        samples_dir = os.path.join(self.settings['samples_root'], boxid)
        sample_id = int(time.time())
        sample_path = os.path.join(samples_dir, '{}.mp3'.format(sample_id))
        metadata_path = os.path.join(samples_dir, '{}.json'.format(sample_id))

        self.extra_log_args = {
            'boxid': boxid,
            'sample_path': sample_path
        }

        if not os.path.isdir(samples_dir):
            os.mkdir(samples_dir)

        with NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
            tmp_file.write(self.request.body)
            yield self.write_metadata(tmp_file.name, metadata_path)
            os.rename(tmp_file.name, sample_path)
