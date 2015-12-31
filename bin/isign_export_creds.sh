#!/usr/bin/env bash

# Export a certificate and key from a .p12 file into PEM form, and place
# them where isign expects them to be.
#
# The .p12 file is typically exported from Apple's Keychain Access.

if [[ $# -eq 0 ]]; then
    echo "Usage: $0 exported.p12 [target_directory]"
    exit 1;
fi

p12_path=$1

if [[ ! -e $p12_path ]]; then
    echo "Can't find $p12_path!";
    exit 1;
fi

target_dir=${2-$HOME/.isign}

target_cert_path=$target_dir/certificate.pem
target_key_path=$target_dir/key.pem

chmod 600 $p12_path

mkdir -p $target_dir
openssl pkcs12 -in $p12_path -out $target_cert_path -clcerts -nokeys
openssl pkcs12 -in $p12_path -out $target_key_path -nocerts -nodes
chmod 600 $target_key_path

read -p "Done exporting $p12_path. Remove it? [Y/n]:" -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm $p12_path
fi
echo "Exported credentials from $p12_path to $target_dir"


read -p "Find matching provisioning profile? [Y/n]:" -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    ./guess_mobileprovision.sh $target_cert_path
fi
