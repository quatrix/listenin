from base_handler import CORSHandler
import jwt

class TokenHandler(CORSHandler):
    _users = {
        'eddie': {'password': 'vova', 'club': 'kulialma'},
        'vova': {'password': 'vova', 'club': 'radio'},
    }

    def get(self):
        username = self.get_argument('username')
        password = self.get_argument('password')

        if self._users[username]['password'] != password:
            self.finish({'token': None})
            return

        club_id = self._users[username]['club']
        secret = self.settings['jwt_secret']

        token = jwt.encode(
            {'club_id': club_id},
            secret,
            algorithm='HS256'
        )

        self.finish({'token': token})
