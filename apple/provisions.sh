#!/bin/bash

usage() {
    echo "./provisions -p [PATH_TO_NEW_PROVISIONING_PROFILE] -c \"CERT NAME: MUST BE IN KEYCHAIN\" ipa_file"
    exit
}

while getopts ":p:c:" opt; do
    case $opt in
        p  )  PRO_PROFILE=$OPTARG ;;
        c  )  CERT_NAME=$OPTARG ;;
        /? )  usage
    esac
done

shift $(($OPTIND - 1))
if [[ -z "$@" ]]; then
    usage
else
    APP=$@
fi

verify_args() {
    if [[ ! -e $APP ]]; then
        echo "$APP does not exist"
        exit 1
    elif [[ ! -e $PRO_PROFILE ]]; then
        echo "$PRO_PROFILE does not exist"
        exit 1
    elif [[ -z $CERT_NAME ]]; then
        echo "Must specify a certificate to use"
        exit 1
    fi
}

is_app() {
    [[ $APP =~ \.app$ ]]
}

is_ipa() {
    [[ $APP =~ \.ipa$ ]]
}

setup_dir() {
    STAGE_DIR=./stage
    ENTITLEMENTS_FILE=$STAGE_DIR/Entitlements.plist
    if [[ -e $STAGE_DIR ]]; then
        rm -r $STAGE_DIR
    fi
    mkdir $STAGE_DIR
    if is_app; then
        cp -r $APP $STAGE_DIR
        APP_NAME=$(basename $APP)
        PAYLOAD_DIR=""
        APP_DIR=$STAGE_DIR/$APP_NAME
    elif is_ipa; then
        unzip -qu $APP -d $STAGE_DIR
        PAYLOAD_DIR=$STAGE_DIR/Payload
        APP_DIR=$PAYLOAD_DIR/*.app
    else
        echo "Must provide either an .app or .ipa file"
        exit 1
    fi
}

copy_profile() {
    cp "$PRO_PROFILE" $APP_DIR/embedded.mobileprovision
}

create_entitlements() {
    /usr/libexec/PlistBuddy -x -c "print :Entitlements " /dev/stdin <<< $(security cms -D -i ${APP_DIR}/embedded.mobileprovision) > $ENTITLEMENTS_FILE
}

sign_app() {
    if [ -e $APP_DIR/Frameworks ]; then
        for dylib in "$APP_DIR/Frameworks/*"
        do
            echo "signing $dylib"
            # entitlements are irrelevant to dylibs
            /usr/bin/codesign -f -s "$CERT_NAME" $dylib
        done
    fi 
    echo "signing $APP_DIR";
    /usr/bin/codesign -f -s "$CERT_NAME" --entitlements $ENTITLEMENTS_FILE $APP_DIR 2>/dev/null
}

package_app() {
    if is_ipa; then
        (cd $STAGE_DIR; zip -qr out.ipa Payload)
        echo "Re-provisioned ipa at $STAGE_DIR/out.ipa"
    else
        echo "Re-provisioned app at $APP_DIR"
    fi
}

verify_args
setup_dir
copy_profile
create_entitlements
sign_app
package_app
