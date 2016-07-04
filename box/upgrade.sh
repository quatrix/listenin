#!/bin/bash

set -e

git pull
.pyenv/bin/pip install -r requirements.txt 
