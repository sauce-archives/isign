#!/bin/bash
set -e
./version.sh json | python -mjson.tool
find . -name '*.pyc' -delete
nosetests
