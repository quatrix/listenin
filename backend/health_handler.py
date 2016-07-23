
from collections import defaultdict

from tornado.gen import coroutine, Return
from base_handler import BaseHandler
from ttldict import TTLDict


class HealthHandler(BaseHandler):
    _health_cache = TTLDict(60)

    @coroutine
    def get_last_blink(self, box):
        try:
            last_blink = yield self.settings['es'].get_last_document(
                host=box,
                message='INFO:root:blink'
            )
        except Exception as e:
            print(e)
            raise Return(None)

        raise Return(last_blink['_source']['@timestamp'])

    @coroutine
    def get_last_upload(self, box):
        try:
            last_upload = yield self.settings['es'].get_last_document(
                boxid=box.split('-')[1],
                message='success'
            )
        except Exception:
            raise Return({'time': None})

        raise Return(last_upload['_source']['@timestamp'])

    @coroutine
    def _get_box_health(self, box):
        box = 'listenin-' + box

        if box not in self._health_cache:
            last_blink = yield self.get_last_blink(box)
            last_upload = yield self.get_last_upload(box)

            self._health_cache[box] = {
                'last_blink': last_blink,
                'last_upload': last_upload,
            }

        raise Return(self._health_cache[box])

    @coroutine
    def get(self):
        box = self.get_argument('box')
        health = yield self._get_box_health(box)
        self.finish({box: health})
