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
      -o <path>, --output <path>
                            Path to output file or directory

If you have credentials in a well-known location (see below) then you can omit most 
of the arguments.

You can also call it from Python:

.. code:: python

    from isign.isign import resign

    success = resign(
      input_path='some.app', 
      output_path='signed.app'
    )

    if success:
      print "re-signed app!"

Note that the app to sign can be an ``.ipa`` file or a ``.app``
directory, or an archive like ``app.tar.gz``, ``app.tgz`` or ``app.zip``. 
``isign`` will produce a re-signed file of the same kind.

See `Keys and certificates <docs/keys_and_certificates.rst>`__ for how to
obtain the credentials, and where to put them so that the library
will use them by default.

A note on OpenSSL
-----------------

The OpenSSL that ships by default with Macs, as of May 2015 (0.9.8zd),
is inadequate. Install OpenSSL >= 1.0.1j with brew. If for whatever
reason you need to still have Apple's openssl around, set the
environment variable OPENSSL to the correct binary and ``isign.py``
will do the right thing.

Packaging
---------

This library is packaged according to the new Sauce standard for 
Python Packages. See `https://saucedev.atlassian.net/wiki/display/AD/Python+packaging` for details
about deploying or modifying this library.

Testing
-------

``./run_tests.sh``

Some tests require Apple's
`codesign <https://developer.apple.com/library/mac/documentation/Darwin/Reference/ManPages/man1/codesign.1.html>`__
to run, so they are skipped unless you run them on a Macintosh computer with developer tools.

The tests assume you have credentials in a well-known location (see above).


Rationale
---------

The iOS kernel will refuse to run an app if it doesn't have an
appropriate signature that it can trace, in various ways, all the way
back to Apple.

This signature is built right into the format of how executables are
laid out on iOS, the LC\_CODE\_SIGNATURE structure in a Mach-O binary.

Apps from the app store are already signed in a way that allows them to
run on any computer. Developers need to get a special 'provisioning' file
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
