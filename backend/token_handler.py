import bcrypt
import json

from base_handler import CORSHandler

def check_password(plain_text_password, hashed_password):
    return bcrypt.checkpw(
        plain_text_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


class TokenHandler(CORSHandler):
    def post(self):
        request = json.loads(self.request.body)

        username = request['username']
        password = request['password']

        user = self.settings['users'].get(username, None)

        if user and check_password(password, user['hashed_password']):
            token = self.create_token({'club_id': user['club_id']})
            self.finish({'token': token})
        else:
            self.finish({'token': None})
