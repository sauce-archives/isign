#!/bin/bash
set -e

# determine local paths
pushd $(dirname $0) >/dev/null
DEV_DIR=$PWD
cd ..
SRC_DIR=$PWD
popd >/dev/null

pip install -r ${DEV_DIR}/requirements.txt
pip install -e ${SRC_DIR}
