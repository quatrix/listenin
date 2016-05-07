import subprocess
import time
import pytz
import datetime


def get_duration(f):
    r = subprocess.check_output(
        ['sox', f, '-n', 'stat'],
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )

    for l in r.split('\n'):
        if l.startswith('Length'):
            return float(l.split()[-1])


def age(t):
    return int(time.time() - t)


def unix_time_to_readable_date(t):
    tz = pytz.timezone('Asia/Jerusalem')
    return datetime.datetime.fromtimestamp(t, tz=tz).strftime('%Y-%m-%d %H:%M:%S')


def number_part_of_sample(sample):
    return int(sample[:-4])


def normalize_acrcloud_response(r):
    r = r['metadata']['music'][0]

    def _get_genres():
        if 'genres' in r:
            return [g['name'] for g in r['genres']]
        return []

    return {
        'album': r['album']['name'],
        'genres': _get_genres(),
            'title': r['title'],
            'artists': [a['name'] for a in r['artists']],
        }
