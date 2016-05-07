from base_handler import BaseHandler
from utils import get_duration
import os
import logging


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
