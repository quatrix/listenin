import requests
import click
import json

es_request = {
  'query': {
    'filtered': {
      'filter': {
        'bool': {
          'must': [
            {
              'constant_score': {
                'filter': {
                  'exists': {
                    'field': 'acrcloud.title'
                  }
                }
              }
            },
            {
              'query': {
                'match': {
                  'message': {
                    'type': 'phrase',
                    'query': 'success'
                  }
                }
              }
            }
          ]
        }
      }
    }
  }
}

def get_recognized_songs(club, limit):
    by_club = {
      'query': {
        'match': {
          'boxid.raw': {
            'type': 'phrase',
            'query': club
          }
        }
      }
    }

    es_request['query']['filtered']['filter']['bool']['must'].append(by_club)
    r = requests.post('http://localhost:9200/_all/_search/?size={}'.format(limit), data=json.dumps(es_request))

    for res in r.json()['hits']['hits']:
        yield res['_source']['acrcloud']


@click.command()
@click.option('--club', help='club name', required=True)
@click.option('--limit', help='how much songs to fetch', default=1000)
def main(club, limit):
    seen = set()

    for song in get_recognized_songs(club, limit):
        song = u'{} {} {}'.format(song['album'], ' '.join(song['artists']), song['title'])
        
        if song not in seen:
            seen.add(song)
            click.echo(song)

if __name__ == '__main__':
    main()
