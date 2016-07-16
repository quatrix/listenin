from base_handler import BaseHandler
import time
import os
import logging
import json
from tempfile import NamedTemporaryFile
from tornado.gen import coroutine, Return
from tornado.process import Subprocess
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
            raise Return(None)

        raise Return(r['metadata']['music'][0])

    @coroutine
    def recognize_sample_with_gracenote(self, sample_path):
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
    def write_metadata(self, sample_path, metadata_path):
        metadata = {}

        try:
            recognized_song = yield self.recognize_sample(sample_path)

            if recognized_song:
                self.extra_log_args['acrcloud'] = normalize_acrcloud_response(recognized_song)
                metadata['recognized_song'] = recognized_song

        except Exception:
            logging.getLogger('logstash-logger').exception('recognize_sample')

        try:
            recognized_song_gn = yield self.recognize_sample_with_gracenote(sample_path)

            if 'error' not in recognized_song_gn:
                self.extra_log_args['gracenote'] = recognized_song_gn
                metadata['gracenote'] = recognized_song_gn

        except Exception:
            logging.getLogger('logstash-logger').exception('recognize_sample_gn')

        try:
            # FIXME: get_duration() should not block
            metadata['duration'] = get_duration(sample_path)
            self.extra_log_args['sample_duration'] = metadata['duration']
        except Exception:
            logging.getLogger('logstash-logger').exception('get_duration')

        try:
            # FIXME: get_bpm() should not block
            metadata['bpm'] = get_bpm(sample_path)
            self.extra_log_args['bpm'] = metadata['bpm']
        except Exception:
            logging.getLogger('logstash-logger').exception('get_bpm')

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
            tmp_file.flush()
            yield self.write_metadata(tmp_file.name, metadata_path)
            os.chmod(tmp_file.name, 0644)
            os.rename(tmp_file.name, sample_path)

        self.settings['samples'].add(sample_id, boxid)
