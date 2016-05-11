from tornado.httpclient import AsyncHTTPClient
from tornado.gen import coroutine, Return
from base_handler import BaseHandler
from collections import defaultdict
import copy
import logging
import json

last_document_query = {
  'query': {
    'bool': {
        'must': []
    }
  },
  'size': 1,
    'sort': [
        {
            '@timestamp': {
                'order': 'desc'
            }
        }
    ]
}


class HealthHandler(BaseHandler):
    def gen_last_document_query(self, **kwarg):
        q = copy.deepcopy(last_document_query)

        for k, v in kwarg.iteritems():
            m = { "match": { k: { "query": v, "type": "phrase" } } }
            q['query']['bool']['must'].append(m)

        return q

    @coroutine
    def query_es(self, query):
        http_client = AsyncHTTPClient()
        res = yield http_client.fetch(
            "{}/_search".format(self.settings['elasticsearch_host']),
             method='GET',
             body=json.dumps(query),
             allow_nonstandard_methods=True
        )

        res = json.loads(res.body)

        if res['hits']['total'] == 0:
            raise RuntimeError('query returned zero results')

        raise Return(res['hits']['hits'][0])

    @coroutine
    def get_last_document(self, **kwargs):
        query = self.gen_last_document_query(**kwargs)
        raise Return((yield self.query_es(query)))

    @coroutine
    def get(self):
        res = defaultdict(dict)

        for box in 'listenin-radio', 'listenin-pasaz':
            try:
                last_blink = yield self.get_last_document(host=box, message='INFO:root:blink')
                res[box]['last_blink'] = last_blink['_source']['@timestamp']
            except Exception:
                logging.exception('get last blink')
            
            try:
                last_color_change = yield self.get_last_document(
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
                last_upload = yield self.get_last_document(
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
