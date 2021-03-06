# -*- coding: utf-8 -*-

import copy
import os
import json
import time

from bo_handler import BOHandler

_CLUBS_FILE = 'clubs.json'

def _get_clubs():
    return json.loads(open(_CLUBS_FILE).read())


def _save_clubs(clubs):
    tmp_clubs_file = '{}.tmp'.format(_CLUBS_FILE)

    with open(tmp_clubs_file, 'w') as f:
        f.write(json.dumps(clubs, indent=4))

    os.rename(tmp_clubs_file, _CLUBS_FILE)


class Clubs(object):
    def __init__(self, samples, base_url, images_version):
        self._clubs = _get_clubs()

        self.samples = samples
        self.base_url = base_url
        self.images_version = images_version

    def remove_overdue_stops(self):
        for club in self._clubs.values():
            for k in BOHandler._stoppers:
                if club[k] in (0, -1):
                    continue

                if int(time.time()) > club[k]:
                    club[k] = 0

    def get_box_id(self, club_id):
        return self._clubs[club_id].get('box_id')

    def get(self, club_id):
        club = copy.deepcopy(self._clubs[club_id])

        club['club_id'] = club_id
        club['logo'] = self.get_logo(club_id)
        club['samples'] = self.samples.all().get(club['box_id'])
        club['cover'] = os.path.join(
            self.get_images_path(),
            club_id,
            self.get_versioned_image('cover.jpg'),
        )

        return club

    def all(self):
        return [self.get(club_id) for club_id in self._clubs.keys()]

    def update(self, club_id, club):
        clubs = copy.deepcopy(self._clubs)
        clubs[club_id].update(club)
        _save_clubs(clubs)
        self._clubs = clubs

    def get_logo(self, club):
        sizes = 'hdpi', 'mdpi', 'xhdpi', 'xxhdpi', 'xxxhdpi'
        prefix = os.path.join(self.get_images_path(), club)

        return {
            size: os.path.join(prefix, self.get_versioned_image('{}.png'.format(size)))
            for size in sizes
        }

    def get_images_path(self):
        return os.path.join(self.base_url, 'images')

    def get_versioned_image(self, image):
        return '{}?version={}'.format(
            image,
            self.images_version
        )
        
    def find_club_by_box_id(self, box_id):
        # FIXME yeah it's o(n) but n is very small 
        # so this should do for now, lookup table in the future

        for club in self._clubs.values():
            if club['box_id'] == box_id:
                return club
    
    def is_recording_on_hold(self, box_id):
        club = self.find_club_by_box_id(box_id)
        return club and club['stopRecording'] != 0

    def is_recognition_on_hold(self, box_id):
        club = self.find_club_by_box_id(box_id)
        return club and club['stopRecognition'] != 0
