#!/bin/bash

# ./build.sh /path/to/isign

# builds various archival formats of the isign test app
# and puts them in the test directory of isign. You have to specify
# isign's source directory on the command line


project=isignTestApp
isign_dir=$1
isign_test_dir=$isign_dir/tests

warn() {
    echo "$@" 1>&2;
}

build_app() {
    local platform=$1;
    local build_dir=build/Release-$(echo $platform | tr -d "0-9.");
    xcodebuild -project $project.xcodeproj -sdk $platform;
}

copy_app() {
    local platform=$1;
    local target=$2;
    local build_dir=$(build_app $platform)
    cp -r $build_dir/$project.app $target;
}

copy_app_zip() {
    local platform=$1;
    local target=$2;
    local build_dir=$(build_app $platform)
    pushd $build_dir;
    rm -f app.zip;
    zip -r app.zip $project.app;
    popd;
    mv $build_dir/app.zip $target;
}


build_ipa() {
    local platform=$1
    local target=$2

    xcodebuild clean -project $project.xcodeproj -configuration Release -sdk $platform;
    xcodebuild archive -project $project.xcodeproj -scheme $project -archivePath $project.xcarchive
    xcodebuild -exportArchive \
               -archivePath $projectname.xcarchive \
               -exportPath $projectname \
               -exportFormat ipa \
               -exportProvisioningProfile "Neil Kandalgaonkar"
}



copy_app     iphoneos9.2        $isign_test_dir/Test.app;
copy_app_zip iphoneos9.2        $isign_test_dir/Test.app.zip;
# build_ipa     iphoneos9.2        $isign_test_dir/Test.ipa;
# build_app_zip iphonesimulator9.2 $isign_test_dir/TestSimulator.app.zip;

