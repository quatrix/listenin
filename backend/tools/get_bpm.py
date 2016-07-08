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
            

def get_bpm_bpm_tools(filename):
    cmd = 'sox {} -t raw -r 44100 -e float -c 1 - | /root/bpm-tools/bpm'.format(filename)
    r = subprocess.check_output(cmd, shell=True)
    return float(r)

def get_bpm_qm(filename):
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

@click.command()
@click.argument('filename', type=click.Path(exists=True))
def main(filename):
    click.echo('bpm [ss]: {}'.format(get_bpm(filename)))
    click.echo('bpm [bt]: {}'.format(get_bpm_bpm_tools(filename)))
    click.echo('bpm [qm]: {}'.format(get_bpm_qm(filename)))
    click.echo('-----')

if __name__ == '__main__':
    main()
