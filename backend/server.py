from tornado.web import Application, RequestHandler
from tornado.ioloop import IOLoop
from tornado.log import enable_pretty_logging
from upload_handler import UploadHandler
from clubs_handler import ClubsHandler
from spy_handler import SpyHandler
from acrcloud.recognizer import ACRCloudRecognizer

import logstash
import logging
import click


@click.command()
@click.option('--port', default=55669, help='Port to listen on')
@click.option('--samples-root', default='/usr/share/nginx/html/listenin.io/uploads/', help='Where files go')
@click.option('--base-url', default='http://listenin.io/', help='Base URL')
@click.option('--n-samples', default=10, help='How many samples to return')
@click.option('--sample-interval', default=300, help='Sampling interval')
@click.option('--max-age', default=3600*2 , help='Oldest sample age')
@click.option('--acr-key', help='ACRCloud Access Key')
@click.option('--acr-secret', help='ACRCloud Access Secret')
def main(port, samples_root, base_url, n_samples, sample_interval, max_age, acr_key, acr_secret):
    logstash_handler = logstash.LogstashHandler('localhost', 5959, version=1)

    logstash_logger = logging.getLogger('logstash-logger')
    logstash_logger.setLevel(logging.INFO)
    logstash_logger.addHandler(logstash_handler)

    acr_config = {
        'host':'eu-west-1.api.acrcloud.com',
        'access_key': acr_key,
        'access_secret': acr_secret,
        'debug':False,
        'timeout':10,
    }

    recognizer = ACRCloudRecognizer(acr_config)

    app = Application([
        (r"/upload/(.+)/", UploadHandler),
        (r"/clubs", ClubsHandler),
        (r"/spy", SpyHandler),
    ], 
        debug=True,
        samples_root=samples_root,
        base_url=base_url,
        n_samples=n_samples,
        sample_interval=sample_interval,
        max_age=max_age,
        recognizer=recognizer,
    )

    enable_pretty_logging()

    app.listen(port, xheaders=True)
    IOLoop.current().start()


if __name__ == "__main__":
    main()
