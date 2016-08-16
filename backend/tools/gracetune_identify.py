#!/usr/bin/env python
from __future__ import print_function

import time
import tempfile
import subprocess
import json

import click
import pygn

@click.command()
@click.option('--client-id', required=True)
@click.option('--user-id')
@click.option('--license', required=True)
@click.option('--filename', required=True)
def main(client_id, user_id, license, filename):
    """
    Takes media files, converts it to 44100 wav file,
    tries to recognize it and returns metadata.
    """

    if user_id is None:
        user_id = pygn.register(client_id)
        click.echo('user_id: {}'.format(user_id))
        return

    with tempfile.NamedTemporaryFile(suffix='.wav') as wav:
        subprocess.check_call(['sox', filename, '-r', '44100', wav.name])
        c_id, tag_id = client_id.split('-')
        res = subprocess.Popen([
            'gracetune_musicid_stream',
            c_id,
            tag_id,
            license,
            'online',
            wav.name
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        stdout, stderr = res.communicate()

        try:
            res = json.loads(stdout)
        except Exception:
            print(json.dumps({'error': stderr}, indent=4))
            return

    if 'error' in res:
        print(json.dumps(res, indent=4))
        return

    for _ in xrange(5):
        try:
            metadata = pygn.search(
                clientID=client_id,
                userID=user_id,
                artist=res['artist'],
                album=res['album'],
                track=res['track'],
            )

            if metadata:
                print(json.dumps(metadata, indent=4))
                return
        except Exception:
            time.sleep(0.5)

    print(json.dumps({'error': 'failed to fetch song details via pygn'}, indent=4))

if __name__ == '__main__':
    main()
