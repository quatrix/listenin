#!/bin/bash

set -e

sudo cp -r /home/pi/listenin/box/etc/systemd/system/sensu-client.service /etc/systemd/system/
sudo systemctl enable sensu-client

sudo update-rc.d sensu-client remove -f
sudo /etc/init.d/sensu-client stop
sudo systemctl enable sensu-client
sudo systemctl start sensu-client
