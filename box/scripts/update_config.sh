#!/bin/bash

set -e
export LC_ALL=C

echo "killing sensu"
sudo killall sensu-client
sudo update-rc.d sensu-client remove -f

echo "enabling sensu systemd"
sudo cp -r /home/pi/listenin/box/etc/systemd/system/sensu-client.service /etc/systemd/system/
sudo systemctl enable sensu-client

echo "starting sensu"
sudo systemctl start sensu-client
