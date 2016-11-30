#!/bin/bash

openssl smime -sign -in test.mobileprovision.plist -outform der -out test.mobileprovision -signer test.cert.pem -inkey test.key.pem -nodetach
