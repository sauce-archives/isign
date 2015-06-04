#!/bin/bash
package_name="iresign"

make_venv() {
    # For some reason mkvirtualenv returns with exit code 1 on success.  So we
    # have to just continue.
    virtualenv $TMPDIR || true
    source $TMPDIR/bin/activate
    pip install -r dev/requirements.txt
}

test_artifacts() {
    rm -rf dist-release && mkdir -p dist-release  # nothing tested for release

    version=$(./version.sh)
    pip install dist/${package_name}-${version}.tar.gz
    ./run_tests.sh
    mv dist/${package_name}-${version}.tar.gz dist-release/
}

build_artifacts() {
    python setup.py sdist
}

cleanup() {
    rm -rf $TMPDIR
}

# to push tags: add the repo to the "bots" team
tag_release() {
    tag="v$(./version.sh)"
    echo "Tagging $head as $tag"
    git tag $tag $head
    git push origin $tag
}


set -e
TMPDIR=$(mktemp -d /tmp/${package_name}.XXXXXXXX)
trap cleanup 0

make_venv
build_artifacts
test_artifacts
tag_release
cleanup
