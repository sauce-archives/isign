#!/bin/bash

# figure out our package name from the name of repo
pushd $(dirname $0) >/dev/null
package_name=$(basename $PWD)
popd >/dev/null

make_venv() {
    # For some reason mkvirtualenv returns with exit code 1 on success.  So we
    # have to just continue.
    virtualenv $TMPDIR || true
    source $TMPDIR/bin/activate
    pip install -r dev/requirements.txt
}

build_artifacts() {
    python setup.py sdist
}

test_artifacts() {
    rm -rf dist-release && mkdir -p dist-release  # nothing tested for release

    version=$(./version.sh)
    pip install dist/${package_name}-${version}.tar.gz
    ./run_tests.sh
    mv dist/${package_name}-${version}.tar.gz dist-release/
}

# to push tags: add the repo to the "bots" team
tag_release() {
    tag="v$(./version.sh)"
    echo "Tagging $head as $tag"
    git tag $tag $head
    git push origin $tag
}

cleanup() {
    rm -rf $TMPDIR
}


set -e
TMPDIR=$(mktemp -d /tmp/${package_name}.XXXXXXXX)
trap cleanup 0

make_venv
build_artifacts
test_artifacts
tag_release
cleanup
