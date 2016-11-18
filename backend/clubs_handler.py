from operator import itemgetter
from geopy import distance
from base_handler import BaseHandler


class ClubsHandler(BaseHandler):
    def get_distance_from_client(self, location):
        client_latlng = self.get_latlng()

        if client_latlng is None:
            return 0

        return int(distance.vincenty(location, client_latlng).meters)

    def get_clubs(self):
        clubs = self.settings['clubs'].all()

        for club in clubs:
            club['distance'] = self.get_distance_from_client(club['location__'])
            
        return sorted(clubs, key=itemgetter('distance'))

    def get(self):
        self.finish({'clubs': self.get_clubs()})
