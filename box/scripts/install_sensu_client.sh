#!/bin/bash

set -e 

wget -q http://sensu.global.ssl.fastly.net/apt/pubkey.gpg -O- | sudo apt-key add -
echo "deb     http://sensu.global.ssl.fastly.net/apt sensu main" | sudo tee /etc/apt/sources.list.d/sensu.list
sudo apt-get update
sudo apt-get install sensu

cp -r /home/pi/listenin/box/etc/sensu /etc/
