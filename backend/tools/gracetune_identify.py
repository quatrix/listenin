#!/usr/bin/env python

import pygn
import click
import subprocess
import json
import tempfile

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
        res = subprocess.check_output(['gracetune_musicid_stream', c_id, tag_id, license, 'online', wav.name])
        res = json.loads(res)

    metadata = pygn.search(
        clientID=client_id,
        userID=user_id,
        artist=res['artist'], 
        album=res['album'],
        track=res['track'],
    )

    print(json.dumps(metadata, indent=4))


if __name__ == '__main__':
    main()
