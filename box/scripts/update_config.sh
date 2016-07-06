#!/bin/bash

set -e
export LC_ALL=C

echo "copying sensu config"
sudo cp -r /home/pi/listenin/box/etc/systemd/system/sensu-client.service /etc/systemd/system/

echo "enabling sensu systemd"
sudo systemctl enable sensu-client
sudo systemctl restart sensu-client
