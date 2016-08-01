from __future__ import print_function
import datetime
import requests
import calendar
import os
import time

from dateutil import tz, parser
from humanize import naturaltime


_mailgun = {
    'key': 'key-32c14a9ca66a0d37282d27ac739dc493',
    'sandbox': 'mg.listenin.io',
}


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


def send_report(subject, body, recipient):
    request_url = 'https://api.mailgun.net/v2/{0}/messages'.format(_mailgun['sandbox'])
    request = requests.post(request_url, auth=('api', _mailgun['key']), data={
        'from': 'no-reply@listenin.io',
        'to': recipient,
        'subject': subject,
        'text': body,
    })
    print(request)


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


def today_at(local_tz):
    utc = datetime.datetime.utcnow()
    utc = utc.replace(tzinfo=tz.gettz('UTC'))
    return utc.astimezone(tz.gettz(local_tz))

def main():
    health = _get_health()

    recipients = ['evil.legacy@gmail.com']
    report = []

    for box_name, box in health.iteritems():
        expected = _get_closing_hour(box_name)
        actual = _utc_to_localtime(box['last_upload'], local_tz=_hours[box_name]['_tz'])

        if actual < expected:
            last_upload = datetime.datetime.now(tz.tzutc()) - parser.parse(box['last_upload'])

            extra_info = ' (expected: {})'.format(expected.strftime('%m/%d %H:%M'))

            if last_upload.total_seconds() > 60 * 60 * 24:
                extra_info = ' ({})'.format(naturaltime(last_upload))

            report.append('{} last sample at {}{}'.format(
                box_name,
                actual.strftime('%m/%d %H:%M'),
                extra_info,
            ))

    
    for recpt in recipients:
        send_report(
            subject='ListenIn health status for {}'.format(today_at('Israel').strftime('%m/%d')),
            body='\n'.join(report),
            recipient=recpt
        )
if __name__ == '__main__':
    main()
