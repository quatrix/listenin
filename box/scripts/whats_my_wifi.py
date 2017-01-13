#!/usr/bin/env python

from __future__ import print_function
from subprocess import check_output, STDOUT, CalledProcessError
from collections import namedtuple
from time import sleep
import uuid
import logging
import urllib2
import json
import sys
import os

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

Wifi = namedtuple('Wifi', ['ssid', 'psk'])

CONNECTIONS_DIR = '/etc/NetworkManager/system-connections/'
API_HOSTNAME = 'api.listenin.io'


CONNECTION_TMPL = """
[connection]
id={ssid}
uuid={uuid}
type=wifi

[wifi]
ssid={ssid}
mode=infrastructure

{security}

[ipv4]
method=auto
"""


SECURITY_TMPL = """
security=802-11-wireless-security

[wifi-security]
key-mgmt=wpa-psk
psk={psk}
"""


def create_nm_file(wifi):
    return CONNECTION_TMPL.format(
        uuid=uuid.uuid4(),
        ssid=wifi.ssid,
        security=SECURITY_TMPL.format(psk=wifi.psk) if wifi.psk else ''
    )
        

def get_token():
    return open('/etc/listenin/token').read()


def get_wifi_from_backend():
    url = 'http://{api_hostname}/bo/wifi?token={token}'.format(
        api_hostname=API_HOSTNAME, 
        token=get_token()
    )

    try:
        response = urllib2.urlopen(url)
        response = json.loads(response.read())
    except Exception:
        logging.exception('get_wifi_from_backend')
        return

    if 'error' in response:
        logging.error(response['error'])
        return
    
    return Wifi(response['ssid'], response.get('psk', ''))


def ssid_to_conn_file(ssid):
    return os.path.join(CONNECTIONS_DIR, ssid)


def get_connection(ssid):
    conn_file = ssid_to_conn_file(ssid)

    if not os.path.exists(conn_file):
        return None

    for line in open(conn_file).readlines():
        line = line.strip().split('=')

        if line[0] == 'psk':
            return Wifi(ssid, line[1])
        
    return Wifi(ssid, '')
    

def is_connected(ssid):
    try:
        return 'IP4.ADDRESS' in check_output(['nmcli', 'c', 'show', ssid])
    except CalledProcessError:
        return False


def run_cmd(cmd):
    try:
        check_output(cmd, stderr=STDOUT)
    except CalledProcessError as exc:
        logging.error('"%s" failed, rc: "%s", output: "%s"', ' '.join(cmd), exc.returncode, exc.output.strip())


def connect(wifi):
    conn_file = ssid_to_conn_file(wifi.ssid)

    with open(conn_file, 'w') as f:
        f.write(create_nm_file(wifi))

    os.chmod(conn_file, 0o600)

    run_cmd(['systemctl', 'restart', 'network-manager'])
    sleep(10)

    run_cmd(['nmcli', 'c', 'up', wifi.ssid])
    sleep(10)

    return is_connected(wifi.ssid)


def setup_wifi(wifi):
    conn = get_connection(wifi.ssid)

    if conn is None:
        logging.info('first time configuring this ssid')
        return connect(wifi)

    if conn.psk == wifi.psk and is_connected(wifi.ssid):
        logging.info('psk is set correctly and connection is up, bye!')
        return True
        
    logging.info('psk changed or connection down, reconfiguring connection')

    return connect(wifi)


def setup_wifi_from_backend(backend_fail_retry=10, connect_fail_retry=60, refresh=300):
    wifi = get_wifi_from_backend()

    if wifi is None:
        logging.error('did not get wifi from backend! retrying in %d seconds', backend_fail_retry)
        sleep(backend_fail_retry)
        return

    logging.info('got wifi from backend: %s', wifi)

    connected = setup_wifi(wifi)

    if connected:
        logging.info('connected to %s sucessully, checking again in %d seconds', wifi.ssid, refresh)
        sleep(refresh)
    else:
        logging.error('failed to connect to %s, retrying in %d seconds', wifi.ssid, connect_fail_retry)
        sleep(connect_fail_retry)


def main():
    while True:
        setup_wifi_from_backend()

if __name__ == '__main__':
    main()
