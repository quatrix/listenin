import subprocess
import time
import datetime
import json
import logging
from tempfile import NamedTemporaryFile

import pytz


def get_bpm(filename):
    with NamedTemporaryFile(suffix='.wav') as wav:
        subprocess.check_call(['sox', filename, '-c', '1', wav.name])

        r = subprocess.check_output(
            ['vamp-simple-host', 'qm-vamp-plugins:qm-tempotracker:tempo', wav.name],
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )

        for l in r.split('\n'):
            if l.endswith('bpm'):
                return float(l.split()[-2])


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
    tz = pytz.timezone('UTC')
    return datetime.datetime.fromtimestamp(t, tz=tz).strftime('%Y-%m-%dT%H:%M:%SZ')


def number_part_of_sample(sample):
    return int(sample.split('.')[0])


def normalize_acrcloud_response(r):
    def _get_genres():
        if 'genres' in r:
            return [g['name'] for g in r['genres']]
        return []

    return {
        'album': r['album']['name'],
        'genres': _get_genres(),
        'title': r['title'],
        'artists': [a['name'] for a in r['artists']],
        '_recognizer': 'acrcloud',
    }

def normalize_gracenote_response(r):
    return {
        'album': r['album_title'],
        'genres': [],
        'title': r['tracks'][0]['track_title'],
        'artists': [r['album_artist_name']],
        '_recognizer': 'gracenote',
    }


def is_same_song(a, b):
    """
    Compares two songs and returns True if they are the same
    """

    for k in 'album', 'title', 'artists':
        if a[k] != b[k]:
            return False

    return True


def get_metadata_from_json(sample_metadata_path):
    """
    Reads a sample metadata json and returns it normalized
    """

    try:
        metadata = json.loads(open(sample_metadata_path).read())
    except IOError:
        logging.exception('get_metadata')
        return

    if 'gracenote' in metadata:
        metadata['recognized_song'] = normalize_gracenote_response(metadata['gracenote'])
        del metadata['gracenote'] # FIXME this is while we're using two recognizers
    elif 'recognized_song' in metadata:
        metadata['recognized_song'] = normalize_acrcloud_response(metadata['recognized_song'])

    return metadata
