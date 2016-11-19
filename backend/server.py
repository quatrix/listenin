from tornado.web import Application, RequestHandler
from tornado.ioloop import IOLoop
from tornado.log import enable_pretty_logging
from upload_handler import UploadHandler
from clubs_handler import ClubsHandler
from spy_handler import SpyHandler
from health_handler import HealthHandler
from samples_cache import SamplesCache
from clubs import Clubs
from bo_handler import BOHandler 
from bo_samples_handler import BOSamplesHandler
from token_handler import TokenHandler

try:
    from acrcloud.recognizer import ACRCloudRecognizer
except ImportError:
    from acrcloud_osx.recognizer import ACRCloudRecognizer

import logstash
import logging
import click


@click.command()
@click.option('--port', default=55669, help='Port to listen on')
@click.option('--samples-root', default='/usr/share/nginx/html/listenin.io/uploads/', help='Where files go')
@click.option('--base-url', default='http://listenin.io/', help='Base URL')
@click.option('--n-samples', default=10, help='How many samples to return')
@click.option('--sample-interval', default=4*60, help='How often should new samples come in')
@click.option('--acr-key', required=True, help='ACRCloud Access Key')
@click.option('--acr-secret', required=True, help='ACRCloud Access Secret')
@click.option('--es-host', default='http://localhost:9200', help='ElasticSearch host')
@click.option('--gn-client-id', required=True, help='Gracenote cliet id')
@click.option('--gn-user-id', required=True, help='Gracenote user id')
@click.option('--gn-license', required=True, help='Gracenote license file')
@click.option('--images-version', required=True, help='Images version number')
@click.option('--jwt-secret', required=True, help='Json Web Token secret')
@click.option('--debug', default=False, help='Debug mode')
def main(port, samples_root, base_url, n_samples, sample_interval, acr_key, acr_secret, es_host, gn_client_id, gn_user_id, gn_license, images_version, jwt_secret, debug):
    logstash_handler = logstash.LogstashHandler('localhost', 5959, version=1)

    logstash_logger = logging.getLogger('logstash-logger')
    logstash_logger.setLevel(logging.INFO)
    logstash_logger.addHandler(logstash_handler)

    enable_pretty_logging()
    logstash_logger.info('Starting Server')

    acr_config = {
        'host':'eu-west-1.api.acrcloud.com',
        'access_key': acr_key,
        'access_secret': acr_secret,
        'debug': False,
        'timeout':10,
    }

    gn_config = {
        'client_id': gn_client_id,
        'user_id': gn_user_id,
        'license': gn_license,
    }

    recognizer = ACRCloudRecognizer(acr_config)

    samples_cache = SamplesCache(
        samples_root=samples_root,
        n_samples=n_samples,
        base_url=base_url,
    )

    clubs = Clubs(
        samples=samples_cache,
        base_url=base_url,
        images_version=images_version,
    )

    app = Application(
        [
            (r"/upload/(.+)/", UploadHandler),
            (r"/clubs", ClubsHandler),
            (r"/bo/samples", BOSamplesHandler),
            (r"/bo", BOHandler),
            (r"/token", TokenHandler),
            (r"/spy", SpyHandler),
            (r"/health", HealthHandler),
        ],
        debug=debug,
        clubs=clubs,
        sample_interval=sample_interval,
        samples_root=samples_root,
        samples=samples_cache,
        recognizer=recognizer,
        gn_config=gn_config,
        jwt_secret=jwt_secret,
    )

    app.listen(port, xheaders=True)
    IOLoop.current().start()


if __name__ == "__main__":
    main()
