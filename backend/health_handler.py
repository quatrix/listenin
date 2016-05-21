from tornado.gen import coroutine, Return
from base_handler import BaseHandler
from collections import defaultdict

import logging
import json


class HealthHandler(BaseHandler):
    @coroutine
    def get_last_blink(self, box):
        try:
            last_blink = yield self.settings['es'].get_last_document(
                host=box,
                message='INFO:root:blink'
            )
        except Exception:
            logging.exception('get last blink')
            raise Return(None)

        raise Return(last_blink['_source']['@timestamp'])

    @coroutine
    def get_last_color(self, box):
        try:
            last_color_change = yield self.settings['es'].get_last_document(
                host=box,
                message='INFO:root:setting led color to'
            )
        except Exception:
            logging.exception('get last color')
            raise Return({'color': None, 'time': None})

        raise Return({
            'color': last_color_change['_source']['message'].split()[-1],
            'time': last_color_change['_source']['@timestamp'],
        })

    @coroutine
    def get_last_upload(self, box):
        try:
            last_upload = yield self.settings['es'].get_last_document(
                boxid=box.split('-')[1],
                message='success'
            )
        except Exception:
            logging.exception('get last upload')
            raise Return({'time': None})

        raise Return({
            'time': last_upload['_source']['@timestamp'],
        })

    @coroutine
    def get(self):
        res = defaultdict(dict)

        for box in 'listenin-radio', 'listenin-pasaz':
            res[box]['last_blink'] = yield self.get_last_blink(box)
            res[box]['last_color'] = yield self.get_last_color(box)
            res[box]['last_upload'] = yield self.get_last_upload(box)

        self.finish(res)
