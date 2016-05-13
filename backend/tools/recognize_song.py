import click
import json

try:
    from acrcloud.recognizer import ACRCloudRecognizer
except ImportError:
    from acrcloud_osx.recognizer import ACRCloudRecognizer

@click.command()
@click.argument('filename', type=click.Path(exists=True))
@click.option('--acr-key', required=True, help='ACRCloud Access Key')
@click.option('--acr-secret', required=True, help='ACRCloud Access Secret')
def main(filename, acr_key, acr_secret):
    config = {
        'host':'eu-west-1.api.acrcloud.com',
        'access_key': acr_key,
        'access_secret': acr_secret,
        'debug':False,
        'timeout':10,
    }

    res = ACRCloudRecognizer(config).recognize_by_file(filename, 0)
    print(json.dumps(json.loads(res), indent=4))

if __name__ == '__main__':
    main()
