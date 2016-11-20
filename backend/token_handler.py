from base_handler import CORSHandler
import bcrypt


def check_password(plain_text_password, hashed_password):
    return bcrypt.checkpw(
        plain_text_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


class TokenHandler(CORSHandler):
    def get(self):
        username = self.get_argument('username')
        password = self.get_argument('password')

        user = self.settings['users'].get(username, None)

        if user and check_password(password, user['hashed_password']):
            token = self.create_token({'club_id': user['club_id']})
            self.finish({'token': token})
        else:
            self.finish({'token': None})
