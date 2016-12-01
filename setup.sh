#!/usr/bin/env bash

apt-get install -y python python-pip python-dev python3 python3-dev
add-apt-repository ppa:fkrull/deadsnakes
apt-get update
apt-get install -y python3.5