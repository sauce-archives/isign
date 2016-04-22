#!/bin/bash

# figure out our package name from the name of repo
pushd $(dirname $0) >/dev/null
package_name=$(basename $PWD)
package=$(echo $package_name | sed 's/-/_/g')
popd >/dev/null

version=$(./version.sh)

# this communicates to setup.py to use the version 
# number we just made, rather than generating another
export PYTHON_PACKAGE_VERSION=${version}

make_venv() {
    # For some reason mkvirtualenv returns with exit code 1 on success.  So we
    # have to just continue.
    virtualenv $TMPDIR || true
    source $TMPDIR/bin/activate
    pip install -r dev/requirements.txt
}

build_release() {
    python setup.py sdist
    release=${package_name}-${version}.tar.gz
}

test_release() {
    rm -rf dist-release && mkdir -p dist-release  

    echo "pip install dist/$release"
    pip install dist/$release
    echo -e "\nInstalled packages:"
    pip freeze -l
    echo
    mv $package ${package}.testing
    ./run_tests.sh
    mv dist/$release dist-release/
}

# to push tags: add the repo to the "bots" team
tag_release() {
    tag="v$version"
    echo "Tagging $head as $tag"
    git tag $tag $head
    git push origin $tag
}

update_pypi() {
    # always succeed with upload - transient errors with pypi 
    # should not cause red build
    twine upload dist-release/$release || true
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
build_release
test_release
tag_release
update_pypi
cleanup
