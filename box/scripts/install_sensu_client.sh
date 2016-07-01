#!/bin/bash

set -e 

source /home/pi/listenin/box/.pyenv/bin/activate
pip install -r /home/pi/listenin/box/requirements.txt

wget -q http://sensu.global.ssl.fastly.net/apt/pubkey.gpg -O- | sudo apt-key add -
echo "deb     http://sensu.global.ssl.fastly.net/apt sensu main" | sudo tee /etc/apt/sources.list.d/sensu.list
apt-get update
apt-get install sensu
cp -r /home/pi/listenin/box/etc/sensu /etc/

update-rc.d sensu-client defaults
/etc/init.d/sensu-client restart
