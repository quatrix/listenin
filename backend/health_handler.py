from tornado.httpclient import AsyncHTTPClient
from tornado.gen import coroutine, Return
from base_handler import BaseHandler
from collections import defaultdict
import logging

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

@coroutine
def get_last_message(es_host, host, message):
    query = es_query.format(host=host, message=message)
    http_client = AsyncHTTPClient()
    res = yield http_client.fetch(
        "{}/_search".format(es_host),
         method='GET',
         body=query,
         allow_nonstandard_methods=True
    )

    if res['hits']['total'] == 0:
        raise RuntimeError('query returned zero results')

    raise Return(res['hits']['hits'][0])

class HealthHandler(BaseHandler):
    @coroutine
    def get(self):
        res = defaultdict(dict)
        es_host = self.settings['elasticsearch_host']

        for box in 'listenin-radio', 'listenin-pasaz':
            try:
                last_blink = yield get_last_message(es_host, box, 'INFO:root:blink')
                res[box]['last_blink'] = last_blink['_source']['@timestamp']
            except Exception:
                logging.exception('get last blink')
            
            try:
                last_color_change = yield get_last_message(
                    es_host,
                    box,
                    'INFO:root:setting led color to'
                )

                res[box]['last_color'] = {
                    'color': last_blink['_source']['message'].split()[-1],
                    'changed_at': last_blink['_source']['@timestamp']
                }
            except Exception:
                logging.exception('get last color')

        self.finish(res)
