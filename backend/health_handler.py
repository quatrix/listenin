from tornado.httpclient import AsyncHTTPClient
from tornado.gen import coroutine, Return
from base_handler import BaseHandler
from collections import defaultdict
import logging
import json

es_query = """
{{
  "query": {{
    "bool": {{
        "must": [
            {{
                "match": {{
                    "host": {{
                        "query": "{host}",
                        "type": "phrase"
                    }}
                }}
            }},
            {{
                "match": {{
                    "message": {{
                        "query": "{message}",
                        "type": "phrase"
                    }}
                }}
            }}
        ]
    }}
  }},
  "size": 1,
    "sort": [
        {{
              "@timestamp": {{
                  "order": "desc"
              }}
        }}
  ]
}}
"""


class HealthHandler(BaseHandler):
    @coroutine
    def get_last_message(self, host, message):
        query = es_query.format(host=host, message=message)
        http_client = AsyncHTTPClient()
        res = yield http_client.fetch(
            "{}/_search".format(self.settings['elasticsearch_host']),
             method='GET',
             body=query,
             allow_nonstandard_methods=True
        )

        res = json.loads(res.body)

        if res['hits']['total'] == 0:
            raise RuntimeError('query returned zero results')

        raise Return(res['hits']['hits'][0])

    @coroutine
    def get(self):
        res = defaultdict(dict)

        for box in 'listenin-radio', 'listenin-pasaz':
            try:
                last_blink = yield self.get_last_message(box, 'INFO:root:blink')
                res[box]['last_blink'] = last_blink['_source']['@timestamp']
            except Exception:
                logging.exception('get last blink')
            
            try:
                last_color_change = yield self.get_last_message(
                    box,
                    'INFO:root:setting led color to'
                )

                res[box]['last_color'] = {
                    'color': last_color_change['_source']['message'].split()[-1],
                    'changed_at': last_color_change['_source']['@timestamp']
                }
            except Exception:
                logging.exception('get last color')

        self.finish(res)
