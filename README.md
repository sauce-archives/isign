# iresign

iOS app signer / re-signer. Does not require OS X.

## Synopsis

    iresign.py [-h] -p <your.mobileprovision> -a <path> -k <path> -c
                      <certificate> [-s <path>] [-o <path>]
                      <path>

    Resign an iOS application with a new identity and provisioning profile.

    positional arguments:
      <path>                Path to application to re-sign, typically a directory
                            ending in .app or file ending in .ipa.

    optional arguments:
      -h, --help            show this help message and exit
      -p <your.mobileprovision>, --provisioning-profile <your.mobileprovision>
                            Path to provisioning profile
      -a <path>, --apple-cert <path>
                            Path to Apple certificate in .pem form
      -k <path>, --key <path>
                            Path to your organization's key in .p12 format
      -c <certificate>, --certificate <certificate>
                            Path to your organization's certificate in .pem form
      -s <path>, --staging <path>
                            Path to stage directory.
      -o <path>, --output <path>
                            Path to output file or directory

## A note on OpenSSL

The OpenSSL that ships by default with Macs, as of May 2015 (0.9.8zd), is inadequate. Install 
OpenSSL 1.0.1j with brew. If for whatever reason you need to still have Apple's openssl around,
set the environment variable OPENSSL to the correct binary and `iresign.py` will do the 
right thing.

## Where to get certificates and keys

We assume you have created the accounts as needed with Apple, and imported all 
the keys and certs into Keychain on a Mac.

**key** In Keychain, locate your private key. Export it as a Personal Information Exchange
(.p12) file.

**certificate** TBD, some sort of [dance](http://stackoverflow.com/questions/1762555/creating-pem-file-for-apns) 
where you export a .cer from Keychain then use openssl to turn it into a .pem? 

**apple certificates** TBD?? How did @sah do this?

## Rationale

The iOS kernel will refuse to run an app if it doesn't have an appropriate signature that
it can trace, in various ways, all the way back to Apple.

This signature is built right into the format of how executables are laid out on iOS,
the LC_CODE_SIGNATURE structure in a Mach-O binary.

Apps from the app store are already signed in a way that allows them to run on any 
computer. Developers need to be a special 'provisioning' file from Apple to test their 
apps on their devices.

So, with Sauce Labs, we have the problem that our customers' apps are almost certainly
provisioned only for their devices. But they need to run on our devices. 

It's relatively easy to re-sign an app using Apple tools, and pretty much everyone that has
needed to do this just uses a Mac anyway. Even if their build system is Linux based, they 
will add a Mac to that somehow, and ssh into it to do signing. 

However, we needed to do signing at scale, and we wanted to avoid 
the problems of adding Mac hardware (or Mac VMs) to our cloud infrastructure. It turns
out that while it was really hard, it's possible to sign apps using entirely OSS tools.


## Testing

To run tests, use [py.test](http://pytest.org). The deeper tests of functionality
require [codesign](https://developer.apple.com/library/mac/documentation/Darwin/Reference/ManPages/man1/codesign.1.html)
to run, so they only run on a Macintosh computer with developer tools.
