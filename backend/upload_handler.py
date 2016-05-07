from base_handler import BaseHandler
from utils import get_duration
import time
import os
import logging
import json
from utils import normalize_acrcloud_response


class UploadHandler(BaseHandler):
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

        try:
            r = self.settings['recognizer'].recognize_by_filebuffer(self.request.body, 0)
            open(metadata_path, 'w').write(r)
            if 'metadata' in r:
                self.extra_log_args['acrcloud'] = normalize_acrcloud_response(json.loads(r))
        except Exception:
            logging.getLogger('logstash-logger').exception('recognize_sample')

        with open(sample_path, 'wb+') as f:
            f.write(self.request.body)

        try:
            self.extra_log_args['sample_duration'] = get_duration(sample_path)
        except Exception:
            logging.getLogger('logstash-logger').exception('get_duration')
