from tornado.escape import json_decode
from base_handler import BaseHandler

class SpyHandler(BaseHandler):
    def post(self):
        self.extra_log_args = json_decode(self.request.body)
