# -*- coding: utf-8 -*-

from __future__ import print_function
from operator import itemgetter
import datetime
import requests
import calendar
import os
import time
import click
import math

from dateutil import tz, parser
import humanize

_mailgun = {
    'key': 'key-32c14a9ca66a0d37282d27ac739dc493',
    'sandbox': 'mg.listenin.io',
}

_ignore_boxes = {'bootleg'}

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

    'bootleg': {
        '_tz': 'Israel',
        '_default': (23, 04),
        'Thursday': (23, 06),
        'Friday': (23, 06),
    },
}


def send_report(subject, html, recipient):
    request_url = 'https://api.mailgun.net/v2/{0}/messages'.format(_mailgun['sandbox'])
    request = requests.post(request_url, auth=('api', _mailgun['key']), data={
        'from': 'no-reply@listenin.io',
        'to': recipient,
        'subject': subject,
        'html': html, 
    })
    print(request.text)


def _get_closing_hour(venue):
    day = today_at(_hours[venue]['_tz'])

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


template = """
<html>
<body>
<pre>
{}
</pre>
</body>
</html>
"""

def create_report(report):
    if not report:
        return template.format('All good in the hood! :)')

    s = '{} issues:'.format(len(report))
    s += '\n' + '-' * len(s) + '\n\n'
    s += '\n'.join(map(itemgetter(1), sorted(report, key=itemgetter(0), reverse=True)))

    return template.format(s)


def format_time_difference(expected, actual):
    expected = expected.replace(hour=0, minute=0, second=0)
    actual = actual.replace(hour=0, minute=0, second=0)
    return humanize.naturaltime(expected - actual)


@click.command()
@click.option('--recp', '-r', multiple=True, required=True)
@click.option('--no-send', '-n', is_flag=True, default=False)
def main(recp, no_send):
    health = _get_health()

    report = []

    for box_name, box in health.iteritems():
        if box_name in _ignore_boxes:
            continue

        expected = _get_closing_hour(box_name)
        actual = _utc_to_localtime(box['last_upload'], local_tz=_hours[box_name]['_tz'])

        if actual < expected:
            if (expected - actual).total_seconds() < 60 * 15:
                continue

            last_upload_delta = datetime.datetime.now(tz.tzutc()) - parser.parse(box['last_upload'])

            if last_upload_delta.total_seconds() > 60 * 60 * 24:
                msg = 'on {} ({})'.format(
                    actual.strftime('%m/%d'),
                    format_time_difference(expected, actual)
                )
            else:
                msg = 'at {} (expected: {})'.format(
                    actual.strftime('%H:%M'),
                    expected.strftime('%H:%M')
                )

            report.append((last_upload_delta, '* {} - last upload {}'.format(box_name, msg)))

    report = create_report(report)
    print(report)

    if no_send:
        return

    for r in recp:
        send_report(
            subject='ListenIn daily health status report ({})'.format(today_at('Israel').strftime('%m/%d')),
            html=report,
            recipient=r,
        )
if __name__ == '__main__':
    main()
