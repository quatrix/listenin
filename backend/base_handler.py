from tornado.web import RequestHandler
from chainmap import ChainMap
import logging
import jwt

class CORSHandler(RequestHandler):
    def get_token(self):
        secret = self.settings['jwt_secret']
        token = self.get_argument('token') 
        return jwt.decode(token, secret, algorithms=['HS256'])

    def create_token(self, data):
        secret = self.settings['jwt_secret']
        return jwt.encode(data, secret, algorithm='HS256')

    def get_club_id(self):
        return self.get_token()['club_id']

    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
        self.set_header("Access-Control-Allow-Headers", "Content-Type, Depth, User-Agent, X-File-Size, X-Requested-With, X-Requested-By, If-Modified-Since, X-File-Name, Cache-Control")

    def options(self, *args, **kwargs):
        self.finish()

class BaseHandler(CORSHandler):
    def get_latlng(self):
        latlng = self.get_argument('latlng', None)

        if latlng is None:
            latlng = self.request.headers.get('X-LatLng')

        try:
            return tuple(map(float, latlng.split(',')))
        except Exception:
            return

    def on_finish(self):
        status_code = self.get_status()

        location = self.get_latlng()
        
        if location:
            location = ','.join(map(str, self.get_latlng()))

        extra = {
            'device_id': self.request.headers.get('X-Device-Id'),
            'geoip': {'location': location},
            'method': self.request.method,
            'uri': self.request.uri,
            'ip': self.request.remote_ip,
            'status_code': status_code,
            'request_time': 1000.0 * self.request.request_time(),
        }

        extra = {k: v for k, v in extra.items() if v is not None}

        if hasattr(self, 'extra_log_args'):
            extra = ChainMap(extra, self.extra_log_args)

        logger = logging.getLogger('logstash-logger')

        if status_code >= 400:
            logger.error('error', extra=extra, exc_info=True)
        else:
            logger.info('success', extra=extra)
