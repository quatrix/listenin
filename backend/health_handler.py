from tornado.gen import coroutine
from base_handler import BaseHandler
from collections import defaultdict

import logging
import json


class HealthHandler(BaseHandler):
    @coroutine
    def get(self):
        res = defaultdict(dict)
        es = self.settings['es']

        for box in 'listenin-radio', 'listenin-pasaz':
            try:
                last_blink = yield es.get_last_document(host=box, message='INFO:root:blink')
                res[box]['last_blink'] = last_blink['_source']['@timestamp']
            except Exception:
                logging.exception('get last blink')
            
            try:
                last_color_change = yield es.get_last_document(
                    host=box,
                    message='INFO:root:setting led color to'
                )

                res[box]['last_color'] = {
                    'color': last_color_change['_source']['message'].split()[-1],
                    'time': last_color_change['_source']['@timestamp']
                }
            except Exception:
                logging.exception('get last color')

            try:
                last_upload = yield es.get_last_document(
                    boxid=box.split('-')[1],
                    message='success'
                )

                song = last_upload.get('acrcloud')

                if song is not None:
                    song = {
                        'album': song.get('album'),
                        'genres': ' '.join(song.get('genres')),
                        'artists': ' '.join(song.get('artists')),
                        'title': song.get('title')
                    }

                res[box]['last_upload'] = {
                    'time': last_upload['_source']['@timestamp'],
                    'song': song,
                }

            except Exception:
                logging.exception('get last upload')

        self.finish(res)
