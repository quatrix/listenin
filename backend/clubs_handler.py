# -*- coding: utf-8 -*-

import copy
from operator import itemgetter

from functools32 import lru_cache
from tornado.gen import coroutine, Return
from ttldict import TTLDict
from geopy import distance
from base_handler import BaseHandler



class ClubsHandler(BaseHandler):
    _genres = TTLDict(default_ttl=60)

    _clubs = {
        'radio': {
            'name': 'Radio EPGB',
            'details': 'An underground dance-bar, live performances during weekdays and parties on the weekend, considers itself home of the Tel-aviv indie scene.',
            'tags': ['D', 'S', 'SM'],
            'address': '7 Shadal St. Tel Aviv',
            'phone': '+972-3-5603636',
            'location': {'lat': 32.06303301410757, 'lng': 34.775075912475586},
            'location__': (32.06303301410757, 34.775075912475586),
            'wifi': 'radio_epgb',
        },
        'pasaz' : {
            'name': 'The Pasáž',
            'details': 'An underground dance-bar that offers food and live performances along with art displays and special themed parties.',
            'tags': ['D', 'S', 'F', 'SM'],
            'address': '94 Allenby St. Tel Aviv',
            'phone': '+972-77-3323118',
            'location': {'lat': 32.0663031, 'lng': 34.7719147},
            'location__': (32.0663031, 34.7719147),
            'wifi': 'whoknows',
        },
        'annaloulou' : {
            'name': 'Anna Loulou',
            'details': 'Anna Loulou',
            'tags': [],
            'address': 'HaPninim 2, Tel Aviv-Yafo, 6803001, Israel',
            'phone': '+972-3-716-8221',
            'location': {'lat': 32.0534479, 'lng': 34.7538248},
            'location__': (32.0534479, 34.7538248),
            'wifi': 'whoknows',
        },
        'limalima' : {
            'name': 'Lima Lima',
            'details': 'Lima Lima',
            'tags': [],
            'address': 'Lilienblum St 42, Tel Aviv-Yafo',
            'phone': '+972-3-560-0924',
            'location': {'lat': 32.0623976, 'lng': 34.7699819},
            'location__': (32.0623976, 34.7699819),
            'wifi': 'limalima.1',
        },
        'rothschild12' : {
            'name': 'Rothschild 12',
            'details': 'Rothschild 12',
            'tags': [],
            'address': 'Rothschild Blvd 12, Tel Aviv-Yafo',
            'phone': '+972-3-510-6430',
            'location': {'lat': 32.062718, 'lng': 34.7704438},
            'location__': (32.062718, 34.7704438),
            'wifi': 'whoknows',
        },
        'hostel51' : {
            'name': 'Hostel 51',
            'details': 'A restaurant / bar that also functions as a tourist hostel, live dj and a versatile menu.',
            'tags': ['T', 'S', 'F', 'SM'],
            'address': 'Yehuda ha-Levi St 51, Tel Aviv-Yafo',
            'phone': '+972-3-527-7306',
            'location': {'lat': 32.0623872, 'lng': 34.7740594},
            'location__': (32.0623872, 34.7740594),
            'wifi': 'whoknows',
        },
        'kulialma' : {
            'name': 'Kuli Alma',
            'details': 'A dance-bar that aims to be an open-space of music and culture and offers,live music, great parties and visual art displays.',
            'tags': ['D', 'S', 'F', 'LA'],
            'address': 'Mikveh Israel St 10, Tel Aviv-Yafo',
            'phone': '+972-3-656-5155',
            'location': {'lat': 32.0622372, 'lng': 34.774789},
            'location__': (32.0622372,34.774789),
            'wifi': 'whoknows',
        },
        'bootleg' : {
            'name': 'Bootleg',
            'details': 'Bootleg',
            'tags': [],
            'address': 'King George St 48, Tel Aviv-Yafo',
            'phone': '+972-52-805-4448',
            'location': {'lat': 32.0743404, 'lng': 34.7759128},
            'location__': (32.0743404,34.7759128),
            'wifi': 'whoknows',
        },
    }

    def get_distance_from_client(self, location):
        client_latlng = self.get_latlng()

        if client_latlng is None:
            return None

        return int(distance.vincenty(location, client_latlng).meters)

    def get_logo(self, club):
        sizes = 'hdpi', 'mdpi', 'xhdpi', 'xxhdpi', 'xxxhdpi'
        prefix = '{}/images/{}'.format(
            self.settings['base_url'],
            club
        )

        return {
            size: '{}/{}.png?version={}'.format(prefix, size, self.settings['images_version'])
            for size in sizes
        }

    def get_clubs_legacy(self):
        res = {}

        for club, samples in self.settings['samples'].all().iteritems():
            res[club] = self._clubs[club]
            res[club]['logo'] = self.get_logo(club)
            res[club]['samples'] = samples

        return res

    @coroutine
    def get_clubs(self):
        clubs = []

        for club_id, samples in self.settings['samples'].all().iteritems():
            if not samples:
                continue

            club = copy.deepcopy(self._clubs[club_id])
            club['logo'] = self.get_logo(club_id)
            club['samples'] = samples
            club['cover'] = '{}/images/{}/cover.jpg?version={}'.format(
                self.settings['base_url'],
                club_id,
                self.settings['images_version'],
            )
            club['distance'] = self.get_distance_from_client(club['location__'])
            clubs.append(club)

        if self.get_latlng() is None:
            raise Return(clubs)

        raise Return(sorted(clubs, key=itemgetter('distance')))

    @coroutine
    def get(self):
        if self.get_argument('sagi', None):
            res = {
                'clubs': (yield self.get_clubs()),
            }

            self.finish(res)
        else:
            self.finish(self.get_clubs_legacy())
