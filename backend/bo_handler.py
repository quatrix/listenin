from datetime import datetime, timedelta
import json
import time

from base_handler import CORSHandler


class BOHandler(CORSHandler):
    def get(self):
        if self.get_argument('club', None):
            club_id = self.get_argument('club')
            club = self.settings['clubs'].get(club_id)
            self.finish(club)

    def post(self):
        club_id = self.get_argument('club')
        request = json.loads(self.request.body)
        stoppers = [
            'stopPublishing',
            'stopRecording',
            'stopRecognition',
        ]

        for k in stoppers:
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

        # FIXME AS FUCK 
        clubs = self.settings['clubs']
        clubs.update(club_id, request)
        self.finish(clubs.get(club_id))
