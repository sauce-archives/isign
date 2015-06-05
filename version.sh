#!/bin/bash
set -e
PACKAGE_NAME="iresign"
MAJMIN_VERSION="0.1"

# figure out our path
pushd $(dirname $0) >/dev/null
working_dir=$PWD
popd >/dev/null
version_json="${working_dir}/$PACKAGE_NAME/version.json"

version_suffix=""
# official version
if [[ "$JOB_NAME" = "$PACKAGE_NAME" ]] && [[ -n "$BUILD_TAG" ]]; then
    patch_version=0
    if [[ -n "$(git tag --list v$MAJMIN_VERSION.0)" ]]; then
        # number of commits since vMAJOR.MINOR.0
        patch_version=$(git rev-list --count $(git describe --tags --match "v${MAJMIN_VERSION}.0" | cut -f 1 -d -)...HEAD)
    fi
    # add post version if built before (i.e., already tagged)
    post_version=$(git tag --contain | wc -l | awk '{print $1}')
    test "$post_version" -gt 0 && version_suffix=".post${post_version}"
# development version
else
    if [[ -n "$(git tag)" ]]; then
        recent_tag=$(git describe --tags | cut -f 1 -d -)
        majmin_version=$(echo $recent_tag | tr "v-." " " | awk '{print $1"."$2}')
        patch_version=$(echo $recent_tag | tr "v-." " " | awk '{print $3}')
        dev_version=$(git rev-list --count ${recent_tag}...HEAD)
    else  # start of dev, nothing tagged
        majmin_version="0.0"
        patch_version="0"
        dev_version=$(git rev-list --count HEAD)
    fi
    version_suffix=".$(date '+%s').dev${dev_version}+${USER}"
fi

version="${majmin_version:-$MAJMIN_VERSION}.${patch_version}${version_suffix}"
json='"version": "'$version'", "commit": "'$(git rev-parse HEAD)'", "build": "'${BUILD_TAG:-"dev"}'"'
# write-out version.json
echo "{${json}}" > $version_json

style="$1"
if [[ "$style" = "json" ]]; then
    cat $version_json
else
    echo $version
fi
