isign
=====

iOS app signer / re-signer. Does not require OS X.

Synopsis
--------

::

    isign.py [-h] -p <your.mobileprovision> 
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
                            Path to your organization's key in .pem format
      -c <certificate>, --certificate <certificate>
                            Path to your organization's certificate in .pem form
      -s <path>, --staging <path>
                            Path to stage directory.
      -o <path>, --output <path>
                            Path to output file or directory

Or, as a Python library, taking advantage of some default arguments:

::

    from isign.isign import resign

    success = resign(
      app='some.app', 
      certificate='mycert.pem',
      key='mykey.pem',
      output_path='signed.app'
    )

    if success:
      print "re-signed app!"

Note that the app to sign can be an ``.ipa`` file or a ``.app``
directory. ``isign`` will produce a re-signed app of the same kind.

See `Keys and certificates <docs/keys_and_certificates.rst>`__ for how to
obtain the keys and certificates.

A note on OpenSSL
-----------------

The OpenSSL that ships by default with Macs, as of May 2015 (0.9.8zd),
is inadequate. Install OpenSSL >= 1.0.1j with brew. If for whatever
reason you need to still have Apple's openssl around, set the
environment variable OPENSSL to the correct binary and ``isign.py``
will do the right thing.

Packaging
---------

This library is packaged similarly to
`https://github.com/saucelabs/lwjp <lwjp>`__. See the documentation
there for information about deploying or modifying this library.

Testing
-------

``./run_tests.sh``

Most tests require Apple's
`codesign <https://developer.apple.com/library/mac/documentation/Darwin/Reference/ManPages/man1/codesign.1.html>`__
to run, so they only run on a Macintosh computer with developer tools.
You'll also need to put your developer key, certificate, and Apple
certificates into your home directory (read the source for details.)

Rationale
---------

The iOS kernel will refuse to run an app if it doesn't have an
appropriate signature that it can trace, in various ways, all the way
back to Apple.

This signature is built right into the format of how executables are
laid out on iOS, the LC\_CODE\_SIGNATURE structure in a Mach-O binary.

Apps from the app store are already signed in a way that allows them to
run on any computer. Developers need to be a special 'provisioning' file
from Apple to test their apps on their devices.

So, with Sauce Labs, we have the problem that our customers' apps are
almost certainly provisioned only for their devices. But they need to
run on our devices.

It's relatively easy to re-sign an app using Apple tools -- see the
``mac`` directory in this repo for sample scripts. Pretty much everyone
else that has needed to do this just uses a Mac anyway. Even if their
build system is Linux-based, they will add a Mac to that somehow, and
ssh into it to do signing.

However, we needed to do signing at scale, and we wanted to avoid the
problems of adding Mac hardware (or Mac VMs) to our cloud
infrastructure. It turns out that while it was really hard, it's
possible to sign apps using entirely OSS tools.
