# -*- coding: utf-8 -*-

import os
import logging
import json
import copy
from operator import itemgetter

from functools32 import lru_cache
from tornado.gen import coroutine, Return
from ttldict import TTLDict
from utils import age, unix_time_to_readable_date, number_part_of_sample, normalize_acrcloud_response
from geopy import distance
from base_handler import BaseHandler


class ClubsHandler(BaseHandler):
    _samples = TTLDict(default_ttl=15)
    _genres = TTLDict(default_ttl=60)

    _clubs = {
        'radio': {
            'name': 'Radio EPGB',
            'details': 'A home for underground music',
            'address': '7 Shadal St. Tel Aviv',
            'phone': '+972-3-5603636',
            'location': {'lat': 32.06303301410757, 'lng': 34.775075912475586},
            'location__': (32.06303301410757, 34.775075912475586),
            'wifi': 'radio_epgb',
        },
        'pasaz' : {
            'name': 'The Pasáž',
            'details': 'The Pasáž (the Passage)',
            'address': '94 Allenby St. Tel Aviv',
            'phone': '+972-77-3323118',
            'location': {'lat': 32.0663031, 'lng': 34.7719147},
            'location__': (32.0663031, 34.7719147),
            'wifi': 'whoknows',
        },
        'annaloulou' : {
            'name': 'Anna Loulou Bar',
            'details': 'Anna Loulou Bar',
            'address': 'HaPninim 2, Tel Aviv-Yafo, 6803001, Israel',
            'phone': '+972-3-716-8221',
            'location': {'lat': 32.0534479, 'lng': 34.7538248},
            'location__': (32.0534479, 34.7538248),
            'wifi': 'whoknows',
        },
        'limalima' : {
            'name': 'Lima Lima Bar',
            'details': 'Lima Lima Bar',
            'address': 'Lilienblum St 42, Tel Aviv-Yafo',
            'phone': '+972-3-560-0924',
            'location': {'lat': 32.0623976, 'lng': 34.7699819},
            'location__': (32.0623976, 34.7699819),
            'wifi': 'limalima.1',
        },
        'rothschild12' : {
            'name': 'Rothschild 12',
            'details': 'Rothschild 12',
            'address': 'Rothschild Blvd 12, Tel Aviv-Yafo',
            'phone': '+972-3-510-6430',
            'location': {'lat': 32.062718, 'lng': 34.7704438},
            'location__': (32.062718, 34.7704438),
            'wifi': 'whoknows',
        },
        'hostel51' : {
            'name': 'Hostel 51',
            'details': 'Hostel 51',
            'address': 'Yehuda ha-Levi St 51, Tel Aviv-Yafo',
            'phone': '+972-3-527-7306',
            'location': {'lat': 32.0623872, 'lng': 34.7740594},
            'location__': (32.0623872, 34.7740594),
            'wifi': 'whoknows',
        },
        'kulialma' : {
            'name': 'Kuli Alma',
            'details': 'Kuli Alma',
            'address': 'Mikveh Israel St 10, Tel Aviv-Yafo',
            'phone': '+972-3-656-5155',
            'location': {'lat': 32.0622372, 'lng': 34.774789},
            'location__': (32.0622372,34.774789),
            'wifi': 'whoknows',
        },
    }

    def _get_samples(self, club):
        path = os.path.join(self.settings['samples_root'], club)
        n_samples = self.settings['n_samples']

        samples = [sample for sample in os.listdir(path) if sample.endswith('.mp3')]

        samples = filter(
            lambda x: age(x) < self.settings['max_age'],
            map(number_part_of_sample, samples)
        )

        return sorted(samples, reverse=True)[:n_samples]

    def _set_ttl(self, club):
        if not self._samples[club]:
            return

        sample_interval = self.settings['sample_interval']
        seconds_since_last_sample = age(self._samples[club][0])

        if seconds_since_last_sample > sample_interval:
            return

        self._samples.set_ttl(
            club,
            sample_interval - seconds_since_last_sample
        )

    def get_samples(self, club):
        if club in self._samples:
            return self._samples[club]

        self._samples[club] = self._get_samples(club)
        self._set_ttl(club)

        return self._samples[club]

    @lru_cache(maxsize=1000)
    def _get_metatata(self, club, sample):
        sample_metadata_path = os.path.join(
            self.settings['samples_root'],
            club, 
            '{}.json'.format(sample)
        )

        if not os.path.exists(sample_metadata_path):
            return

        r = open(sample_metadata_path).read()

        if len(r) == 0:
            return

        r = json.loads(r)

        if 'metadata' not in r:
            return

        return normalize_acrcloud_response(r)

    def get_metadata(self, club, sample):
        try:
            return self._get_metatata(club, sample)
        except Exception:
            logging.exception('get_metadata')

    def get_distance_from_client(self, location):
        client_latlng = self.get_latlng()

        if client_latlng is None:
            return None

        return int(distance.vincenty(location, client_latlng).meters)

    def enrich_samples(self, samples, club):
        return [{
            'date': unix_time_to_readable_date(sample),
            'link': '{}/uploads/{}/{}.mp3'.format(
                self.settings['base_url'],
                club,
                sample
            ),
            'metadata': self.get_metadata(club, sample),
        } for sample in samples]

    def get_logo(self, club):
        sizes = 'hdpi', 'mdpi', 'xhdpi', 'xxhdpi', 'xxxhdpi'
        prefix = '{}/images/{}'.format(
            self.settings['base_url'],
            club
        )

        return {
            size: '{}/{}.png'.format(prefix, size)
            for size in sizes
        }

    def get_clubs_legacy(self):
        res = {}

        for club in os.listdir(self.settings['samples_root']):
            res[club] = self._clubs[club]
            res[club]['logo'] = self.get_logo(club)

            samples = self.get_samples(club)
            samples = self.enrich_samples(samples, club)
            res[club]['samples'] = samples

        return res

    @coroutine
    def get_clubs(self):
        clubs = []

        for club_id in os.listdir(self.settings['samples_root']):
            club = copy.deepcopy(self._clubs[club_id])

            samples = self.get_samples(club_id)

            if not samples:
                continue

            samples = self.enrich_samples(samples, club_id)

            club['logo'] = self.get_logo(club_id)
            club['samples'] = samples
            club['cover'] = '{}/images/{}/cover.jpg'.format(self.settings['base_url'], club_id)
            club['cover_disabled'] = club['cover'].replace('.jpg', '-gs.jpg')
            club['distance'] = self.get_distance_from_client(club['location__'])

            try:
                club['genres'] = (yield self.get_genres('now-4h', club_id))
            except Exception:
                pass

            clubs.append(club)

        if self.get_latlng() is None:
            raise Return(clubs)

        raise Return(sorted(clubs, key=itemgetter('distance')))

    @coroutine
    def get_genres(self, time_back, club=''):
        key = '{}::{}'.format(time_back, club)

        genres = self._genres.get(key)

        if genres is None:
            kwargs = {}

            if club:
                kwargs = {'boxid': club}

            genres = yield self.settings['es'].get_terms('acrcloud.genres.raw', time_back, **kwargs)
            self._genres[key] = genres

        raise Return(genres)

    @coroutine
    def get(self):
        if self.get_argument('sagi', None):
            try:
                genres = yield self.get_genres('now-6h')
            except Exception:
                genres = []

            res = {
                'clubs': (yield self.get_clubs()),
                'genres': genres,
            }

            self.finish(res)
        else:
            self.finish(self.get_clubs_legacy())
