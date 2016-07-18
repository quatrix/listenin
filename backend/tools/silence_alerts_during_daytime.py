#!/usr/bin/env python
from sh import sensu_cli
import datetime
import json
import click
import os
import time


VENUE_CLOSED = 'VENUE_CLOSED'

def get_venues():
    clients = json.loads(str(sensu_cli('client', 'list', '-f', 'json')))
    stashes = json.loads(str(sensu_cli('stash', 'list', '-f', 'json')))
    ignored = set()

    for stash in stashes:
        path = stash['path'].split('/')
        if path[0] == 'silence' and stash['content']['reason'].strip() not in ['', VENUE_CLOSED]:
            ignored.add(path[1])

    return [
        client['name'] for client in clients
        if 'box' in client['subscriptions'] and client['name'] not in ignored
    ]


def is_weekend():
    return datetime.datetime.today().weekday() in (3, 4)


def is_between(now, start, end):
    if start <= end:
        return start <= now < end
    else:
        return start <= now or now < end


def seconds_between(now, end):
    end = datetime.datetime.today().replace(hour=end, minute=0, second=0)

    if now > end:
        end += datetime.timedelta(days=1)

    return int((end - now).total_seconds())

def silence(venue, ttl):
    click.echo(venue + ' ' + click.style('silencing alerts for {} seconds'.format(ttl) , fg='green'))
    sensu_cli('silence', venue, '--reason', VENUE_CLOSED, '--expire', ttl)


def unsilence(venue):
    click.echo(venue + ' ' + click.style('unsilencing alerts', fg='red'))
    sensu_cli('stash', 'delete', 'silence/{}'.format(venue))


def set_timezone(tz):
    os.environ['TZ'] = tz
    time.tzset()

@click.command()
@click.option('--opening-hour', type=click.Choice(range(24)), default=22)
@click.option('--closing-hour', type=click.Choice(range(24)), default=2)
@click.option('--closing-hour-weekend', type=click.Choice(range(24)), default=6)
@click.option('--timezone', default='Israel')
def main(opening_hour, closing_hour, closing_hour_weekend, timezone):
    set_timezone(timezone)

    if is_weekend():
        closing_hour = closing_hour_weekend

    now = datetime.datetime.now()
    venue_is_open = is_between(
        now.time(),
        datetime.time(opening_hour),
        datetime.time(closing_hour),
    )

    for venue in get_venues():
        if venue_is_open:
            unsilence(venue)
        else:
            silence(venue, ttl=seconds_between(now, opening_hour))
        

if __name__ == '__main__':
    main()
