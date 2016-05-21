from tornado.httpclient import AsyncHTTPClient
from tornado.gen import coroutine, Return
from datetime import date, timedelta

import json
import copy

class ES(object):
    _last_document_query = {
      'query': {
        'bool': {
            'must': []
        }
      },
      'size': 1,
        'sort': [
            {
                '@timestamp': {
                    'order': 'desc',
                    'ignore_unmapped': True,
                }
            }
        ]
    }

    _terms_query = {
      'query': {
        'bool': {
            'must': []
        }
      },
      "size": 0,
      "aggs": {
        "2": {
          "terms": {
            "field": "",
            "size": 10,
            "order": {
              "_count": "desc"
            }
          }
        }
      },
    }

    def __init__(self, eshost):
        self.eshost = eshost

    def gen_and_phrase(self, **kwargs):
        q = []

        for k, v in kwargs.iteritems():
            q.append({ "match": { k: { "query": v, "type": "phrase" } } })

        return q

    def gen_last_document_query(self, **kwargs):
        q = copy.deepcopy(self._last_document_query)
        q['query']['bool']['must'] = self.gen_and_phrase(**kwargs)
        return q

    @coroutine
    def query_es(self, query, index='_all'):
        http_client = AsyncHTTPClient()
        res = yield http_client.fetch(
            "{}/{}/_search".format(self.eshost, index),
             method='GET',
             body=json.dumps(query),
             allow_nonstandard_methods=True
        )

        res = json.loads(res.body)

        if res['hits']['total'] == 0:
            raise RuntimeError('query returned zero results')

        raise Return(res)

    @coroutine
    def get_last_document(self, index='logstash', **kwargs):
        query = self.gen_last_document_query(**kwargs)

        today, yesterday = date.today(), date.today() - timedelta(1)

        index = ','.join([
            '{}-{}'.format(index, d.strftime('%Y.%m.%d'))
             for d in today, yesterday
        ])


        res = yield self.query_es(query, index=index)
        raise Return(res['hits']['hits'][0])

    @coroutine
    def get_terms(self, field, time_back, **kwargs):
        query = copy.deepcopy(self._terms_query)
        query['aggs']['2']['terms']['field'] = field

        time_back = {
            "range": {
                "@timestamp": {
                    "gte": time_back,
                    "lte": "now"
                }
            }
        }

        query['query']['bool']['must'].append(time_back)
        query['query']['bool']['must'] += self.gen_and_phrase(**kwargs)

        res = yield self.query_es(query)
        raise Return(res['aggregations']['2']['buckets'])
