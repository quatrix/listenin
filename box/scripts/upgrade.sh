#!/bin/bash

set -e

cd /home/pi/listenin/box/
git pull
.pyenv/bin/pip install -r requirements.txt 
