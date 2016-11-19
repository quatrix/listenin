# -*- coding: utf-8 -*-

import copy
import os
import json


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

    def get(self, club_id):
        club = copy.deepcopy(self._clubs[club_id])

        club['logo'] = self.get_logo(club_id)
        club['samples'] = self.samples.all()[club_id]
        club['cover'] = os.path.join(
            self.get_images_path(),
            club_id,
            self.get_versioned_image('cover.jpg'),
        )

        return club

    def all(self):
        clubs = []

        for club_id, samples in self.samples.all().iteritems():
            if not samples or club_id not in self._clubs:
                continue

            clubs.append(self.get(club_id))

        return clubs

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
