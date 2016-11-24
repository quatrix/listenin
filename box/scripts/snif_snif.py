#!/usr/bin/env python

import os
import glob
import csv
import sys
import json
import urllib2
import subprocess
from time import mktime, strptime, sleep
from StringIO import StringIO

def timestr_to_unixtime(s):
    # 2016-11-23 17:20:28 
    fmt = '%Y-%m-%d %H:%M:%S'
    return int(mktime(strptime(s, fmt)))


def parse_capture_file(filename):
    stations = open(filename).read()
    stations = stations.split('\r\n\r\n')[1]
    stations = StringIO(stations)
    return list(csv.reader(stations))[1:]


def normalize_station(station):
    station = [s.strip() for s in station]

    mac = station[0]
    first_seen = timestr_to_unixtime(station[1])
    last_seen = timestr_to_unixtime(station[2])
    power = int(station[3])
    packets = int(station[4])
    bssid = station[5] if station[5] != '(not associated)' else None
    probed_essid = station[6] if station[6] else None

    return [mac, first_seen, last_seen, power, packets, bssid, probed_essid]



def send_to_hq(url, stations):
    req = urllib2.Request(url)
    req.add_header('Content-Type', 'application/json')
    response = urllib2.urlopen(req, json.dumps(stations))
    print(response.read())


def parse_and_send(url, filename):
    stations = [normalize_station(s) for s in parse_capture_file(filename)]
    send_to_hq(url, stations)


def sniff(how_long, interface):
    output_file_prefix = '/tmp/captured'

    map(os.unlink, glob.glob('{}-*.csv'.format(output_file_prefix)))
    subprocess.check_call(['/sbin/iwconfig', interface, 'mode', 'monitor'])
    p = subprocess.Popen(['/usr/sbin/airodump-ng', interface, '-w', output_file_prefix, '--output-format', 'csv'])
    sleep(how_long)
    p.terminate()

    return '{}-01.csv'.format(output_file_prefix)

def main(interface, host):
    url = 'http://listenin.io:5152/wifis/{}/'.format(host)
    output_file = sniff(10, interface)

    parse_and_send(url, output_file)


if __name__ == '__main__':
    main(*sys.argv[1:3])
