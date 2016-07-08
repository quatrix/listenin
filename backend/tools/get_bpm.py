import click
import json
import sys
from tempfile import NamedTemporaryFile
import subprocess

sys.path.insert(0, '../')

def get_bpm(filename):
    with NamedTemporaryFile(suffix='.wav') as wav:
        subprocess.check_call(['sox', filename, wav.name])

        r = subprocess.check_output(
            ['soundstretch', wav.name, '-bpm'],
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )

        for l in r.split('\n'):
            if l.startswith('Detected BPM rate'):
                return float(l.split()[-1])
            


@click.command()
@click.argument('filename', type=click.Path(exists=True))
def main(filename):
    click.echo('bpm: {}'.format(get_bpm(filename)))

if __name__ == '__main__':
    main()
