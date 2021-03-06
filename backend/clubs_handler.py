from operator import itemgetter
import copy
import time
from geopy import distance
from base_handler import BaseHandler


def is_club_not_live(club):
    last_sample_dt = time.time() - club['samples'][0]["_created"]
    return last_sample_dt > 600


class ClubsHandler(BaseHandler):
    def get_distance_from_client(self, location):
        client_latlng = self.get_latlng()

        if client_latlng is None:
            return 0

        return int(distance.vincenty(location, client_latlng).meters)

    def filtered_samples(self, samples):
        def remove_recognized_song(sample):
            sample = copy.deepcopy(sample)

            if sample['metadata']['keep_unrecognized']:
                del sample['metadata']['recognized_song']

            return sample

        return [
            remove_recognized_song(sample)
            for sample in samples
            if not sample['metadata']['hidden']
        ]

    def get_clubs(self):
        clubs = [
            club
            for club in self.settings['clubs'].all()
            if club['stopPublishing'] == 0 and club['samples']
        ]

        for club in clubs:
            club['samples'] = self.filtered_samples(club['samples'])
            club['distance'] = self.get_distance_from_client(club['location'])
            club['location__'] = club['location']

            # remove hidden fields
            for k in club.keys():
                if k.startswith('_'):
                    del club[k]

        return sorted(
            sorted(clubs, key=itemgetter('distance')),
            key=is_club_not_live
        )

    def get(self):
        self.finish({'clubs': self.get_clubs()})
