#!/bin/bash

# figure out our package name from the name of repo
pushd $(dirname $0) >/dev/null
package_name=$(basename $PWD)
package=$(echo $package_name | sed 's/-/_/g')
popd >/dev/null

version=$(./version.sh)


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

    pip install dist/${package_name}-${version}.tar.gz
    echo -e "\nInstalled packages:"
    pip freeze -l
    echo
    mv $package ${package}.testing
    ./run_tests.sh
    mv dist/${package_name}-${version}.tar.gz dist-release/
}

# to push tags: add the repo to the "bots" team
tag_release() {
    tag="v$version"
    echo "Tagging $head as $tag"
    git tag $tag $head
    git push origin $tag
}

update_pypi() {
    python setup.py sdist upload -r pypi
}

cleanup() {
    rm -rf $TMPDIR

    if [[ -d ${package}.testing ]]; then
        mv ${package}.testing $package
    fi
}


set -e
TMPDIR=$(mktemp -d /tmp/${package_name}.XXXXXXXX)
trap cleanup 0

make_venv
build_artifacts
test_artifacts
tag_release
update_pypi
cleanup
