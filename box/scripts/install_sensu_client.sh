#!/bin/bash

set -e 

export LC_ALL=C
BOX_NAME=$(hostname | cut -d- -f2)
source /home/pi/listenin/box/.pyenv/bin/activate
pip install -r /home/pi/listenin/box/requirements.txt

wget -q http://sensu.global.ssl.fastly.net/apt/pubkey.gpg -O- | sudo apt-key add -
echo "deb     http://sensu.global.ssl.fastly.net/apt sensu main" | sudo tee /etc/apt/sources.list.d/sensu.list
sudo apt-get update
sudo apt-get install sensu
sudo cp -r /home/pi/listenin/box/etc/sensu /etc/
sudo cp -r /home/pi/listenin/box/etc/systemd/system/sensu-client.service /etc/systemd/system/
sudo perl -p -i -e "s/BOX_NAME/${BOX_NAME}/g" /etc/sensu/conf.d/client.json

sudo systemctl enable sensu-client
sudo systemctl start sensu-client
