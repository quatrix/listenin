import click
import requests
import json


def get_all_logstash_indicies():
    r = requests.get('http://localhost:9200/_cat/indices?pretty')
    return sorted([l.split()[2] for l in r.text.split('\n') if l])
    

def create_alias_request(index, boxid):
    return {
        "actions": [{
            "add": {
                "index": index,
                "alias": index.replace('logstash', boxid),
                "filter": {
                    "term": {
                        "boxid.raw": boxid
                    }
                }
            }
        }]
    }

def create_alias(index, boxid):
    req  = create_alias_request(index, boxid)
    res = requests.post('http://localhost:9200/_aliases', data=json.dumps(req))
    print(res.text)

@click.command()
@click.option('--boxid', required=True)
def main(boxid):
    for index in get_all_logstash_indicies():
        create_alias(index, boxid) 


if __name__ == '__main__':
    main()
