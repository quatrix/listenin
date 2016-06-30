import sys
from datetime import datetime
import requests
import click
from dateutil import parser
from dateutil.relativedelta import relativedelta
from dateutil.tz import tzutc

MINUTE = 60

OK = 0
CRITICAL = 2
UNKNOWN = 2

@click.command()
@click.option('--health-api', default='http://api.listenin.io/health')
@click.option('--box-name', help='listenin box to monitor', required=True)
@click.option('--upload-threshold', help='how long without uploads is critical', default=5 * MINUTE)
def main(health_api, box_name, upload_threshold):
    health = requests.get(health_api).json()
    box_name = 'listenin-' + box_name

    try:
        box = health[box_name]
    except KeyError:
        click.echo('{} not found in health api'.format(box_name))
        return UNKNOWN

    if box['last_blink'] is None:
        click.echo('{} hasn\'t blinked for more than two days'.format(box_name))
        return CRITICAL

    if box['last_upload']['time'] is None:
        click.echo('{} hasn\'t uploaded for more than two days'.format(box_name))
        return CRITICAL

    now = datetime.now(tzutc())
    last_blink = now - parser.parse(box['last_blink'])
    last_upload = now - parser.parse(box['last_upload']['time'])

    if last_blink.total_seconds() > 5 * MINUTE:
        click.echo('{} hasn\'t blinked for {}'.format(box_name, last_blink))
        return CRITICAL

    if last_upload.total_seconds() > upload_threshold:
        click.echo('{} hasn\'t uploaded for {}'.format(box_name, last_upload))
        return CRITICAL

    return OK


if __name__ == '__main__':
    sys.exit(main())
