# iresign

iOS app signer / re-signer. Does not require OS X.

## Synopsis

    iresign.py [-h] -p <your.mobileprovision> 
                    -a <path to applecerts.pem> 
                    -k <path to your key in .p12 form> 
                    -c <path to your cert in .pem form>
                    [-s <staging path>] 
                    [-o <output path>]
                    <path to app to resign>

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

Note that the app to sign can be an `.ipa` file or a `.app` directory. `iresign` will
produce a re-signed app of the same kind.

## A note on OpenSSL

The OpenSSL that ships by default with Macs, as of May 2015 (0.9.8zd), is inadequate. Install 
OpenSSL >= 1.0.1j with brew. If for whatever reason you need to still have Apple's openssl around,
set the environment variable OPENSSL to the correct binary and `iresign.py` will do the 
right thing.

## Where to get certificates and keys

### Account

We already have an account for the Real Device Cloud, not owned by any single developer, tied to the
`mobdev@saucelabs.com` mail alias. Look in Passpack for the details about how to sign into this account.

If you want to make your own account, say for development on your
own machine: first, find an administrator for our developer organization at
Apple. At this moment, @neilk, @filmaj, and @admc are all admins. Get them to 
invite you to the organization under your @saucelabs.com account, in the iOS Developer Program.

You'll get email from Apple, which will prompt you to set up your account. Set up passwords and 
so on as usual.

**Troubleshooting:** you may have to click on 
the mailed invite link once to set up your account, and then return to your mail to click 
on that invite link again to actually activate your account. Also, in general, things on the Apple site
work better with Safari, so if something doesn't work, try that browser.

### Setting up credentials for iresign

#### Apple certificates

The `applecerts.pem` file can be constructed by these steps. In theory you can export them from 
Keychain Access, but when I tried it the certs were outdated. I think there's a way to update 
them, but this procedure worked for me:

```bash
    $ curl 'https://www.apple.com/appleca/AppleIncRootCertificate.cer' > AppleIncRootCertificate.cer
    $ curl 'http://developer.apple.com/certificationauthority/AppleWWDRCA.cer' > AppleWWDRCA.cer
    $ openssl x509 -inform der -in AppleIncRootCertificate.cer -outform pem -out AppleIncRootCertificate.pem
    $ openssl x509 -inform der -in AppleWWDRCA.cer -outform pem -out AppleWWDRCA.pem
    $ cat AppleWWDRCA.pem AppleIncRootCertificate.pem > applecerts.pem
```

Here's a conceptual explanation of what we're doing:

Download the following certs from [Apple's Certificate Authority Page](https://www.apple.com/certificateauthority/)

* Apple Inc. Root Certificate
* Worldwide Developer Relations Certificate

Then convert these to [PEM](http://en.wikipedia.org/wiki/Privacy-enhanced_Electronic_Mail) format.

Then, concatenate them together. **This file can now serve as the 'apple certs' for code signing.**

#### Your keys and certificates

If you intend to use this account to sign apps for later testing with Appium, it's important that 
everything in this account be for "Developer", not "Distribution". At this moment, Appium uses 
Instruments to install apps and otherwise control the phone, and Instruments won't touch an app that
is signed for Distribution. (Incidentally, welcome to [Richard Stallman's nightmare](http://www.gnu.org/philosophy/right-to-read.en.html).)

The following procedure works as of May 2015, for adding a new account from scratch. You need to use a Mac to follow
these instructions, as they rely on Apple tools to get you started.

Log into your Apple account.

Go to *Certificates, Identifiers, & Profiles*.

Go to *Certificates > Development* in the left-hand column.

Press the plus icon to add a new certificate.

It will ask what type of certificate you need. If this account is meant to sign apps for Appium testing, 
select *iOS App Development*.

It will then instruct you to use Keychain Access to generate a Certificate Signing Request. In effect you are 
going to create a private/public key pair, and then make a little file that says "Hey Apple, please sign this public key 
and make a certificate for it, thus associating both keys with my Apple account!"

Follow the instructions and save that CSR to disk. Press Continue.

Then, the Apple website will ask you to upload that CSR. Do so, and it will create a certificate for your account in your
organization. This certificate might need to be approved by an admin before you can download it.

Once it's approved, download it!

It will probably be named something generic like `ios_development.cer`, so rename it to something more meaningful and
put it somewhere safe.

Import that .cer into Keychain. Keychain will detect that it has an associated private key, and 
in views where you see keys, the certificate will be "inside" the key, and vice versa.

Finally, let's export these.

In Keychain Access, open the *Keys*. Find the key you created and export it as a `.p12` file. If Keychain asks you for
a password to protect this file, just leave it blank. **This is your key file**.

In Keychain Access, open the *Certificates*. Find the certificate you created and export it as a `.cer' file. Then,
convert it to a `.pem` file with `openssl`:

```bash
    $ openssl x509 -inform der -in <your.cer> -outform pem -out <your.pem>
```

This PEM file can now serve as **your certificate file for code signing**.

#### Provisioning profile

One more hoop to jump through. Apple will allow you to sign an app, but it will only work on a number of devices which
have been registered with Apple. We will be registering each of those devices as we deploy them. For the moment, our
development iOS devices are also in the same pool.

We just need to tell Apple that your user is allowed to deploy on those devices. The file that proves this is 
called a provisioning profile.

In the Developer portal, go to *Provisioning Profiles*, and create a new development profile. (You can modify an old one, but it's
painful -- the existing versions of the profile expire or something.)

In *Select App ID*, use 'iOS RDC' -- I think anything with our Apple organizational unit plus dot-star works (`JWKXD469L2.\*`)

Next, in 'Select certificates', select the certificates you want, which probably includes the  you care about.



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

It's relatively easy to re-sign an app using Apple tools -- see the `mac` directory in this repo
for sample scripts. Pretty much everyone else that has
needed to do this just uses a Mac anyway. Even if their build system is Linux-based, they 
will add a Mac to that somehow, and ssh into it to do signing. 

However, we needed to do signing at scale, and we wanted to avoid 
the problems of adding Mac hardware (or Mac VMs) to our cloud infrastructure. It turns
out that while it was really hard, it's possible to sign apps using entirely OSS tools.

## CodeDirectory slots

A signature is mostly composed of hashes of blocks of the file's contents.
However, at some point, Apple added special hashes so the state of
other resources in the app could be captured in the signature. For instance,
the Info.plist gets its own hash, and ultimately the hashes of all the other
files are also captured in the ResourceDirectory hash. Together, all these
special hashes are called the CodeDirectory.

Perhaps to indicate that these are special hashes, they were given
negative offsets in the list of hashes.

For instance, if you do `codesign -d -r- --verbose=20 some.app`

    Executable=...
    Identifier=com.somecompany.someapp
    Format=bundle with Mach-O universal (armv7 arm64)
    CodeDirectory v=20200 size=874 flags=0x0(none) hashes=35+5 location=embedded
    Hash type=sha1 size=20
        -5=0ea763a5bc4d19b0e03315a956deecd97693a661
        -4=0000000000000000000000000000000000000000
        -3=b353e6ce8464fd8ae32cfcf09e7c9015b7378054
        -2=32a5edb9b03a0bea2d7bc30cfdddadab7dab841c
        -1=46ebe92997b23b2e2187a21714c8cc32c347bf35
         0=70e024fdab3426c375cf283d384de58ec6fff438
         1=1ceaf73df40e531df3bfb26b4fb7cd95fb7bff1d
         2=1ceaf73df40e531df3bfb26b4fb7cd95fb7bff1d
         ...

The CodeDirectory hashes have stable negative indices - for instance, -1 is always
the hash of the Info.plist file. The indices for the CodeDirectory hashes are 
sometimes called slots. 

When building the CodeDirectory, We need to observe these constraints:

* Executables should have all 5 slots in their
  codedirectory

* Dylibs only need 2 slots, but sometimes have been
  compiled with 5

* Dylibs should never include the ResourceDir slot, even
  if they have 5 slots

* We should delay calculating hashes until we know we are going
  to use them

* Nobody uses the Application-specific slot anyway

* At least so far, we don't need to change the Info.plist
  slot when re-signing


## Testing

To run tests, use [py.test](http://pytest.org). The deeper tests of functionality
require [codesign](https://developer.apple.com/library/mac/documentation/Darwin/Reference/ManPages/man1/codesign.1.html)
to run, so they only run on a Macintosh computer with developer tools. You'll also need to put your 
developer key, certificate, and Apple certificates into your home directory (read the source for
details.)
