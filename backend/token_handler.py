import bcrypt
import json
from copy import copy

from tornado.web import HTTPError
from base_handler import CORSHandler

def check_password(plain_text_password, hashed_password):
    return bcrypt.checkpw(
        plain_text_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


class TokenHandler(CORSHandler):
    def _authenticate(self):
        username = self._request()['username']
        password = self._request()['password']
        user = copy(self.settings['users'].get(username))

        if not check_password(password, user['hashed_password']):
            raise HTTPError(403)

        del user['hashed_password']
        return user

    def _request(self):
        if not hasattr(self, '_req'):
            self._req = json.loads(self.request.body)
        return self._req

    def _create_token(self):
        user = self._authenticate()

        if user is None:
            return

        if user.get('admin', False) and 'payload' in self._request():
            return self.create_token(self._request()['payload'])

        return self.create_token(user)

    def post(self):
        self.finish({'token': self._create_token()})
