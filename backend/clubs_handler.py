from base_handler import BaseHandler
from ttldict import TTLDict
from utils import age, unix_time_to_readable_date, number_part_of_sample
import os
import time
import logging
import json


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

    def _get_metatata(self, club, sample):
        sample_metadata_path = os.path.join(
            self.settings['samples_root'],
            club, 
            '{}.json'.format(sample)
        )

        if not os.path.exists(sample_metadata_path):
            return

        r = json.loads(open(sample_metadata_path).read())

        if 'metadata' not in r:
            return

        r = r['metadata']['music'][0]
        
        def _get_genres():
            if 'genres' in r:
                return [g['name'] for g in r['genres']]
            return []

        return {
            'album': r['album']['name'],
            'genres': _get_genres(),
            'title': r['title'],
            'artists': [a['name'] for a in r['artists']],
        }

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

    def get(self):
        res = {}

        for club in os.listdir(self.settings['samples_root']):
            res[club] = self._clubs[club]
            res[club]['logo'] = self.get_logo(club)
            
            samples = self.get_samples(club)
            samples = self.enrich_samples(samples, club)
            res[club]['samples'] = samples
            
        self.finish(res)
