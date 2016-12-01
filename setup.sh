#!/usr/bin/env bash

apt-get install -y python python-pip python-dev python3 python3-dev
add-apt-repository ppa:fkrull/deadsnakes
apt-get update
apt-get install -y python3.5

# export CLOUD_SDK_REPO="cloud-sdk-$(lsb_release -c -s)"
# echo "deb http://packages.cloud.google.com/apt $CLOUD_SDK_REPO main" | tee /etc/apt/sources.list.d/google-cloud-sdk.list
# curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -
# apt-get update && apt-get install -y google-cloud-sdk
# gcloud init --console-only