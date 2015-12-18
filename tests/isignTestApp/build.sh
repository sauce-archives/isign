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

project=isignTestApp

# this project just has one scheme configured, same name as project
scheme=$project

# This file must exist in this directory.
export_options_plist=exportOptions.plist


warn() {
    echo "$@" 1>&2;
}

platform_to_build_dir() {
    echo build/Release-$(echo $1 | tr -d "0-9.");
}

build_app() {
    local platform=$1;
    xcodebuild -project $project.xcodeproj -sdk $platform >&2;
}

copy_app() {
    local platform=$1;
    local target=$2;
    build_app $platform
    local build_dir=$(platform_to_build_dir $platform);
    rm -r $target
    cp -r $build_dir/$project.app $target;
}

copy_app_zip() {
    local platform=$1;
    local target=$2;
    build_app $platform
    local build_dir=$(platform_to_build_dir $platform);
    pushd $build_dir;
    rm -f app.zip;
    zip -r app.zip $project.app;
    popd;
    mv $build_dir/app.zip $target;
}

copy_ipa() {
    local platform=$1
    local target=$2

    archive_path=build/$project.xcarchive
    ipa_dir=build
    ipa_path=$ipa_dir/$project.ipa
    rm -f $ipa_path;
    
    xcodebuild clean -project $project.xcodeproj -configuration Release -sdk $platform;
    xcodebuild archive -project $project.xcodeproj -scheme $scheme -archivePath $archive_path;
    xcodebuild -exportArchive \
               -archivePath $archive_path \
               -exportPath $ipa_dir \
               -exportOptionsPlist $export_options_plist 

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

copy_app     iphoneos9.2 $isign_test_dir/Test.app;
copy_app_zip iphoneos9.2 $isign_test_dir/Test.app.zip;
copy_ipa     iphoneos9.2 $isign_test_dir/Test.ipa;
copy_app_zip iphonesimulator9.2 $isign_test_dir/TestSimulator.app.zip;

