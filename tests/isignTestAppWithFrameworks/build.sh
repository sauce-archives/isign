#!/bin/bash

# ./build.sh /path/to/isign

# builds various archival formats of the isign test app
# and puts them in the test directory of isign. You have to specify
# isign's source directory on the command line
#
# Also you have to have the provisioning profile mentioned configured
# in the app. 
#

isign_test_dir=..

projectName=isignTestApp

# workspace
workspace=$projectName.xcworkspace

# this projectName just has one scheme configured, same name as projectName
scheme=$projectName

# This file must exist in this directory.
export_options_plist=exportOptions.plist

warn() {
    echo "$@" 1>&2;
}

copy_ipa() {
    local platform=$1
    local target=$2

    archive_path=build/$projectName.xcarchive
    ipa_dir=build
    ipa_path=$ipa_dir/$projectName.ipa
    rm -f $ipa_path;
    
    xcodebuild clean -workspace $workspace \
                     -scheme $scheme \
                     -configuration Release \
                     -sdk $platform;
    xcodebuild archive -workspace $workspace \
                       -scheme $scheme \
                       -archivePath $archive_path;
    xcodebuild -exportArchive \
               -archivePath $archive_path \
               -exportPath $ipa_dir \
               -exportOptionsPlist $export_options_plist;

    cp $ipa_path $target;
}



if [[ -n $rvm_path ]]; then
    warn "========";
    warn ""
    warn "ACHTUNG!! "
    warn "rvm users! switch to the system version of ruby with: ";
    warn "    $ rvm use system";
    warn "otherwise your path to some ruby development tools like ipatool may be wrong";
    warn ""
    warn "========";
fi

copy_ipa     iphoneos9.2 $isign_test_dir/TestWithFrameworks.ipa;

