import sys
from datetime import datetime
import requests
from dateutil import parser
from dateutil.relativedelta import relativedelta
from dateutil.tz import tzutc

MINUTE = 60

OK = 0
CRITICAL = 2
UNKNOWN = 2

API_URL = 'http://api.listenin.io/health'
UPLOAD_THRESHOLD = MINUTE * 5

def main(box_name):
    health = requests.get(API_URL).json()
    box_name = 'listenin-' + box_name

    try:
        box = health[box_name]
    except KeyError:
        print('{} not found in health api'.format(box_name))
        return UNKNOWN

    if box['last_blink'] is None:
        print('{} hasn\'t blinked for more than two days'.format(box_name))
        return CRITICAL

    if box['last_upload']['time'] is None:
        print('{} hasn\'t uploaded for more than two days'.format(box_name))
        return CRITICAL

    now = datetime.now(tzutc())
    last_blink = now - parser.parse(box['last_blink'])
    last_upload = now - parser.parse(box['last_upload']['time'])

    if last_blink.total_seconds() > 5 * MINUTE:
        print('{} hasn\'t blinked for {}'.format(box_name, last_blink))
        return CRITICAL

    if last_upload.total_seconds() > UPLOAD_THRESHOLD:
        print('{} hasn\'t uploaded for {}'.format(box_name, last_upload))
        return CRITICAL

    return OK


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('usage: {} <box-name>'.format(sys.argv[0]))
        sys.exit(UNKNOWN)
        
    sys.exit(main(sys.argv[1]))
