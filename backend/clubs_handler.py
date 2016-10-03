# -*- coding: utf-8 -*-

import copy
import os
from operator import itemgetter

from functools32 import lru_cache
from tornado.gen import coroutine, Return
from ttldict import TTLDict
from geopy import distance
from base_handler import BaseHandler


class TAGS(object):
    """
    Clubs tag constants
    """

    DANCE_FLOOR = "Dancing"
    TABLES = "Tables"
    LGBT = "LGBT"
    SMOKERS = "Smoking"
    FOOD = "Food"
    SMALL = "Small"
    LARGE = "Large"


class ClubsHandler(BaseHandler):
    _genres = TTLDict(default_ttl=60)

    _clubs = {
        'radio': {
            'name': 'Radio EPGB',
            'details': 'Literally an underground dance-bar, live performances during weekdays and parties on the weekend, considers itself home of the Tel-aviv indie scene.',
            'tags': [TAGS.DANCE_FLOOR, TAGS.SMALL, TAGS.SMOKERS],
            'address': '7 Shadal St. Tel Aviv',
            'phone': '+972-3-5603636',
            'location': {'lat': 32.06303301410757, 'lng': 34.775075912475586},
            'location__': (32.06303301410757, 34.775075912475586),
            'wifi': 'radio_epgb',
        },
        'pasaz' : {
            'name': 'The Pasáž',
            'details': 'An underground dance-bar that offers food and live performances along with art displays and special themed parties.',
            'tags': [TAGS.DANCE_FLOOR, TAGS.SMOKERS, TAGS.FOOD, TAGS.SMALL],
            'address': '94 Allenby St. Tel Aviv',
            'phone': '+972-77-3323118',
            'location': {'lat': 32.0663031, 'lng': 34.7719147},
            'location__': (32.0663031, 34.7719147),
            'wifi': 'whoknows',
        },
        'annaloulou' : {
            'name': 'Anna Loulou',
            'details': '"Describing itself as a cross between underground bar and cultural center, this gay- and smoker-friendly hipster bar is perhaps the only joint in town where Arab and Jewish locals party together." - Lonely Planet',
            'tags': [TAGS.SMOKERS, TAGS.SMALL],
            'address': 'HaPninim 2, Tel Aviv-Yafo, 6803001, Israel',
            'phone': '+972-3-716-8221',
            'location': {'lat': 32.0534479, 'lng': 34.7538248},
            'location__': (32.0534479, 34.7538248),
            'wifi': 'whoknows',
        },
        'limalima' : {
            'name': 'Lima Lima',
            'details': '"The Lima Lima Bar hosts some of Tel Aviv’s best parties. Known for its epic Monday Lima Day gay-friendly Hip Hop nights, Thursday Old School Hip Hop parties, and Friday’s Mainstream Madness line." - secrettelaviv.com',
            'tags': [TAGS.SMALL, TAGS.DANCE_FLOOR],
            'address': 'Lilienblum St 42, Tel Aviv-Yafo',
            'phone': '+972-3-560-0924',
            'location': {'lat': 32.0623976, 'lng': 34.7699819},
            'location__': (32.0623976, 34.7699819),
            'wifi': 'limalima.1',
        },
        'rothschild12' : {
            'name': 'Rothschild 12',
            'details': '"Equally good for lunch, afternoon coffee, aperitifs or late-night drinks. The soundtrack comes courtesy of jazz disks during the day and live bands and DJs at night." - Lonely planet',

            'tags': [TAGS.SMOKERS, TAGS.SMALL, TAGS.TABLES],
            'address': 'Rothschild Blvd 12, Tel Aviv-Yafo',
            'phone': '+972-3-510-6430',
            'location': {'lat': 32.062718, 'lng': 34.7704438},
            'location__': (32.062718, 34.7704438),
            'wifi': 'whoknows',
        },
        'hostel51' : {
            'name': 'Hostel 51',
            'details': 'A restaurant / bar that also functions as a tourist hostel, live dj and a versatile menu.',
            'tags': [TAGS.TABLES, TAGS.SMOKERS, TAGS.SMALL, TAGS.FOOD],
            'address': 'Yehuda ha-Levi St 51, Tel Aviv-Yafo',
            'phone': '+972-3-527-7306',
            'location': {'lat': 32.0623872, 'lng': 34.7740594},
            'location__': (32.0623872, 34.7740594),
            'wifi': 'whoknows',
        },
        'bootleg' : {
            'name': 'Bootleg',
            'details': '"The Bootleg holds a selection of lines on Thursdays and Fridays that attract some extreme clubbers alongside unknowing new visitors. Playing cutting edge music that goes from Progressive Trance to Techno and beyond." (telavivguide.net)',
            'tags': [TAGS.DANCE_FLOOR, TAGS.LARGE],
            'address': 'King George St 48, Tel Aviv-Yafo',
            'phone': '+972-52-805-4448',
            'location': {'lat': 32.0743404, 'lng': 34.7759128},
            'location__': (32.0743404,34.7759128),
            'wifi': 'whoknows',
        },
        'tahat' : {
            'name': 'Tahat',
            'details': '"This latest addition to the club scene draws crowds in a relaxed atmosphere. People come to dance on a rather explosive mix, which mixes rave, hip-hop and techno" - petitfute.com',
            'tags': [TAGS.DANCE_FLOOR, TAGS.LARGE],
            'address': 'Ibn Gavirol St 106, Tel Aviv-Yafo',
            'phone': '+972-52-666-6666',
            'location': {'lat': 32.08418, 'lng': 34.7794211},
            'location__': (32.08418,34.7794211),
            'wifi': 'whoknows',
        },
        'abraxas' : {
            'name': 'Abraxas',
            'details': '"Abraxas is the place to go for some downright quality music, with each night seeing a different line of music, accompanied by a high quality bar with a rich menu" - israeltripplanner.com',
            'tags': [TAGS.SMALL, TAGS.DANCE_FLOOR, TAGS.SMOKERS],
            'address': 'Lilienblum St 40, Tel Aviv-Yafo',
            'phone': '+972-3-510-4435',
            'location': {'lat': 32.0622576, 'lng': 34.7720148},
            'location__': (32.0622576,34.7720148),
            'wifi': 'whoknows',
        },
        'sputnik' : {
            'name': 'Sputnik',
            'details': '"It’s the one place where you will find an outstanding content, underground music and culture futuristic elements of design mixed with retro 70’s and 80’s vibes." - mindspace.me',
            'tags': [TAGS.DANCE_FLOOR],
            'address': 'Allenby St 122, Tel Aviv-Yafo',
            'phone': '+972-52-642-6532',
            'location': {'lat': 32.0628612, 'lng': 34.7730134},
            'location__': (32.0628612,34.7730134),
            'wifi': 'whoknows',
        },
    }

    def get_distance_from_client(self, location):
        client_latlng = self.get_latlng()

        if client_latlng is None:
            return None

        return int(distance.vincenty(location, client_latlng).meters)

    def get_images_path(self):
        return os.path.join(self.settings['base_url'], 'images')

    def get_versioned_image(self, image):
        return '{}?version={}'.format(image, self.settings['images_version'])

    def get_logo(self, club):
        sizes = 'hdpi', 'mdpi', 'xhdpi', 'xxhdpi', 'xxxhdpi'
        prefix = os.path.join(self.get_images_path(), club)

        return {
            size: os.path.join(prefix, self.get_versioned_image('{}.png'.format(size)))
            for size in sizes
        }

    def get_clubs_legacy(self):
        res = {}

        for club, samples in self.settings['samples'].all().iteritems():
            if club not in self._clubs:
                continue

            res[club] = self._clubs[club]
            res[club]['logo'] = self.get_logo(club)
            res[club]['samples'] = samples

        return res

    @coroutine
    def get_clubs(self):
        clubs = []

        for club_id, samples in self.settings['samples'].all().iteritems():
            if not samples or club_id not in self._clubs:
                continue

            club = copy.deepcopy(self._clubs[club_id])
            club['logo'] = self.get_logo(club_id)
            club['samples'] = samples
            club['cover'] = os.path.join(
                self.get_images_path(),    
                club_id,
                self.get_versioned_image('cover.jpg'),
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
