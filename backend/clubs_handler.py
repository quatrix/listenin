# -*- coding: utf-8 -*-

from base_handler import BaseHandler
from functools32 import lru_cache
from ttldict import TTLDict
from utils import age, unix_time_to_readable_date, number_part_of_sample, normalize_acrcloud_response
from geopy import distance
import os
import time
import logging
import json
import copy


class ClubsHandler(BaseHandler):
    _samples = TTLDict(default_ttl=15)
    _clubs = {
        'radio': {
            'name': 'Radio EPGB',
            'details': 'A home for underground music',
            'address': '7 Shadal St. Tel Aviv',
            'phone': '03-5603636',
            'location': { 
                'lat': 32.06303301410757, 
                'lng': 34.775075912475586,
            },
            'wifi': 'radio_epgb',
        },
        'pasaz' : {
            'name': 'The Pasáž',
            'details': 'The Pasáž (the Passage)',
            'address': '94 Allenby St. Tel Aviv',
            'phone': '077-3323118',
            'location': { 
                'lat': 32.0663031,
                'lng': 34.7719147,
            },
            'wifi': 'whoknows',
        }
    }

    def _get_samples(self, club):
        path = os.path.join(self.settings['samples_root'], club)
        n_samples = self.settings['n_samples']
        time_now = time.time()

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
        sizes = 'hdpi', 'mdpi', 'xhdpi', 'xxhdpi','xxxhdpi'
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

    def cmp_distance_to_user(self, a, b):
        client = self.get_latlng()
        
        distance_to_a = distance.vincenty((a['lat'], a['lng']), client)
        distance_to_b = distance.vincenty((b['lat'], b['lng']), client)

        return int(distance_to_a.meters - distance_to_b.meters)

    def get_clubs(self):
        clubs = []

        for club in os.listdir(self.settings['samples_root']):
            samples = self.get_samples(club)
            samples = self.enrich_samples(samples, club)

            club = copy.deepcopy(self._clubs[club])
            club['logo'] = self.get_logo(club)
            club['samples'] = samples

            clubs.append(club)
        
        if self.get_latlng() is None:
            return clubs

        return sorted(
            clubs,
            key=lambda club: club['location'],
            cmp=self.cmp_distance_to_user
        )

    def get(self):
        if self.get_argument('sagi', None):
            self.finish({'clubs': self.get_clubs()})
        else:
            self.finish(self.get_clubs_legacy())

