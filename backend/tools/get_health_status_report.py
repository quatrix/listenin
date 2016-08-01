from __future__ import print_function
import datetime
import requests
import calendar
import os
import time

from dateutil import tz, parser
from humanize import naturaltime


_hours = {
    'radio': {
        '_tz': 'Israel',
        '_default': (22, 04),
        'Thursday': (22, 06),
        'Friday': (22, 06),
    },

    'kulialma': {
        '_tz': 'Israel',
        '_default': (23, 04),
        'Thursday': (23, 06),
        'Friday': (23, 06),
    },

    'pasaz': {
        '_tz': 'Israel',
        '_default': (22, 02),
        'Thursday': (22, 04),
        'Friday': (22, 04),
    },

    'annaloulou': {
        '_tz': 'Israel',
        '_default': (21, 04),
        'Sunday': 'Closed',
    },

    'limalima': {
        '_tz': 'Israel',
        '_default': (23, 05),
        'Sunday': 'Closed',
    },

    'rothschild12': {
        '_tz': 'Israel',
        '_default': (19, 03),
    },

    'hostel51': {
        '_tz': 'Israel',
        '_default': (19, 03),
    },
}


def _get_closing_hour(venue):
    day = datetime.datetime.today()

    while True:
        day -= datetime.timedelta(days=1)
        day_name = calendar.day_name[day.weekday()]
        hours = _hours[venue].get(day_name, _hours[venue]['_default'])

        if hours == 'Closed':
            continue

        if hours[0] > hours[1]:
            day += datetime.timedelta(days=1)

        return day.replace(
            hour=hours[1],
            minute=0,
            second=0,
            microsecond=0,
            tzinfo=tz.gettz(_hours[venue]['_tz'])
        )


def _get_health():
    return requests.get('http://api.listenin.io/health?box=all').json()


def _utc_to_localtime(d, local_tz):
    utc = datetime.datetime.strptime(d, '%Y-%m-%dT%H:%M:%SZ')
    utc = utc.replace(tzinfo=tz.gettz('UTC'))
    return utc.astimezone(tz.gettz(local_tz))


def main():
    health = _get_health()

    for box_name, box in health.iteritems():
        expected = _get_closing_hour(box_name)
        actual = _utc_to_localtime(box['last_upload'], local_tz=_hours[box_name]['_tz'])

        if actual < expected:
            last_upload = datetime.datetime.now(tz.tzutc()) - parser.parse(box['last_upload'])

            extra_info = ' (expected: {})'.format(expected.strftime('%m/%d %H:%M%z'))

            if last_upload.total_seconds() > 60 * 60 * 24:
                extra_info = ' ({})'.format(naturaltime(last_upload))

            print('{} last sample at {}{}'.format(
                box_name,
                actual.strftime('%m/%d %H:%M%z'),
                extra_info,
            ))

if __name__ == '__main__':
    main()
