#!/usr/bin/env bash

# given the filename certificate in PEM form, find potentially matching .mobileprovision files
# in the usual directory on Mac OS X

PROVISIONING_PROFILE_DIR="$HOME/Library/MobileDevice/Provisioning Profiles"

cert_path=${1-$HOME/.isign/certificate.pem}

echo "Looking for provisioning profiles signed with $cert_path..."

get_cert() {
    cert_path=$1
    in_certificate=1
    certificate=''
    while read line; do
        if [[ $line =~ 'BEGIN CERTIFICATE' ]]; then
            in_certificate=0
            continue
        fi
        if [[ $line =~ 'END CERTIFICATE' ]]; then
            in_certificate=1
            continue
        fi
        if [[ $in_certificate -eq 0 ]]; then
            # trim leading/trailing whitespace
            line="$(echo -e $line | sed -e 's/^[[:space:]]*//' | sed -e 's/[[:space:]]*$//')"
            certificate="${certificate}${line}"
        fi
    done < $cert_path
    echo $certificate
}

target_cert=$(get_cert $cert_path)
find "$PROVISIONING_PROFILE_DIR/mobdev1.mobileprovision" -type f -print0 | while IFS= read -r -d '' mobileprovision; do
    # extract the cert from the mobileprovision with `security`
    mobileprovision_data=$(security cms -D -i "$mobileprovision")
    # PlistBuddy doesn't give array lengths, so we don't know how many certs this mobileprovision might have. Try a few
    for i in `seq 0 10`; do
        # because Plistbuddy is dumb, we have to use a convoluted shell syntax to read from stdin 
        # finally base64 it so we can do an easy string comparison
        # TODO: can't quite figure out why, but I need to pipe it to base64, can't do that encoding later.
        # But this means I can't figure out if the PlistBuddy succeeded or failed, by checking $?
        # Have to swallow the error, iterate more times than necessary :(
        cert=$(/usr/libexec/PlistBuddy -c "Print :DeveloperCertificates:$i" /dev/stdin <<< $(echo $mobileprovision_data) 2>/dev/null | base64)
        # Examine a long prefix (there are some issues with padding & zeroes at the end).
        # if first thousand match it is almost certainly a match
        if [[ ${cert:0:1000} = ${target_cert:0:1000} ]]; then
            echo "\"$mobileprovision\" was signed with this certificate."
        fi
    done
done



