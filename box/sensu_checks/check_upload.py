"""
check upload script

"""
from __future__ import print_function

import sys
from datetime import datetime
import argparse
import requests
from dateutil import parser
from dateutil.tz import tzutc
from humanize import naturaltime

OK = 0
CRITICAL = 2
UNKNOWN = 2

MINUTE = 60
API_URL = 'http://api.listenin.io/health?box={}'


def check_upload(box_name, upload_threshold):
    """Checks last upload time for box_name and returns Nagios"""

    try:
        headers = {'Cache-Control': 'no-cache'}
        response = requests.get(API_URL.format(box_name), headers=headers)
        response.raise_for_status()
    except Exception as e:
        print('{} failed getting health from backend: {}'.format(box_name, e))
        return UNKNOWN

    try:
        health = response.json()
    except Exception as e:
        print('{} failed decoding health response: {}'.format(box_name, e))
        return UNKNOWN

    if 'last_upload' not in health:
        print('{} last_upload not found in health results'.format(box_name))
        return UNKNOWN
        
    last_upload = datetime.now(tzutc()) - parser.parse(health['last_upload'])

    if last_upload.total_seconds() > upload_threshold:
        print('{} last uploaded {}'.format(box_name, naturaltime(last_upload)))
        return CRITICAL

    print('{} last upload {}'.format(box_name, naturaltime(last_upload)))
    return OK


def main():
    """
    main entry point
    """

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('box_name', help='box name')
    arg_parser.add_argument('--upload-threshold', type=int, help='threshold (minutes)', default=10)
    args = arg_parser.parse_args()

    return check_upload(
        box_name=args.box_name,
        upload_threshold=args.upload_threshold * MINUTE
    )

if __name__ == '__main__':
    sys.exit(main())
