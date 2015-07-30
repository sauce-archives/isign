#!/bin/bash

# look for required apps
for app in unzip zip; do
    if ! which $app >/dev/null; then
        echo "Missing application: $app"
        exit 1
    fi
done

set -e
./version.sh json | python -mjson.tool
find . -name '*.pyc' -delete
nosetests
