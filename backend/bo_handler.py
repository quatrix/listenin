from tornado.web import HTTPError
from datetime import datetime, timedelta
import json
import copy
import time

from base_handler import CORSHandler
from schema import Schema, And


class BOHandler(CORSHandler):
    _stoppers = [
        'stopPublishing',
        'stopRecording',
        'stopRecognition',
    ]

    _schema = Schema({
        'details': And(basestring, lambda s: 1 <= len(s) <= 250),
        'tags': [And(basestring, lambda s: 1 <= len(s) <= 10)],
        'stopPublishing': int,
        'stopRecording': int,
        'stopRecognition': int,
    }, ignore_extra_keys=True)

    def get(self):
        club_id = self.get_club_id()
        club = self.settings['clubs'].get(club_id)
        self.finish(club)

    def _transform_stop_requests(self, request):
        request = copy.deepcopy(request)

        for k in self._stoppers:
            if request[k] == 0:
                continue

            if request[k] == -1:
                continue

            if request[k] > 100:
                continue

            now = datetime.now()
            future_time = now + timedelta(hours=request[k])
            future_time = future_time.timetuple()
            future_time = int(time.mktime(future_time))

            request[k] = future_time

        return request

    def post(self):
        club_id = self.get_club_id()
        request = json.loads(self.request.body)

        request = self._schema.validate(request)
        request = self._transform_stop_requests(request)

        clubs = self.settings['clubs']
        clubs.update(club_id, request)
        self.finish(clubs.get(club_id))


class BOWifiHandler(CORSHandler):
    def get(self):
        box_id = self.get_club_id()
        clubs = self.settings['clubs']
        club = clubs.find_club_by_box_id(box_id)

        if club is None:
            self.finish({'error': 'box {} not assigned'.format(box_id)})

        if '_wifi' not in club:
            self.finish({'error': 'club {} has no wifi'.format(club['name'])})

        self.finish(club['_wifi'])
