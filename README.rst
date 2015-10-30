isign
=====

A tool and library to re-sign iOS applications, without proprietary Apple software.

For example, an iOS app in development would probably only run on the developer's iPhone. 
``isign`` can alter the app so that it can run on another developer's iPhone.

Apple tools already exist to do this. But with ``isign``, now you can do this on operating
systems like Linux.


Where to get it
---------------

The latest version can be installed via `PyPi <https://pypi.python.org/pypi/isign/>`__:

.. code::

  $ pip install isign

or:

.. code::

  $ easy_install isign

The `source code repository <https://github.com/saucelabs/isign>`__ 
and `issue tracker <https://github.com/saucelabs/isign/issues>`__ 
are maintained on GitHub.


How to get started
------------------

Ensure `openssl <https://www.openssl.org>`__ is at version 1.0.1j or better. 

You'll probably want `libimobiledevice <http://www.libimobiledevice.org/>`__,
so you can try installing your re-signed apps.

You'll need an Apple Developer Account. Obtaining everything you need is
beyond the scope of this documentation, but if you're already making apps
and running them on real iOS devices, you have everything you need.

You should have a key and certificate in Keychain Access, and a provisioning 
profile associated with that certificate, that you can use to sign iOS apps 
for one or more of your own iOS devices.

**Caution:** We're going to be exporting important and private information 
out of Keychain Access. Keep these files secure, especially your private key.

First, make the .isign directory:

.. code::

  $ mkdir ~/.isign

Next, export your key and certificate from Keychain Access. In Keychain Access, 
open the *Keys*. Find the key you use to sign apps. Your certificate will 
appear as a "descendant" of this key. Right click on it and 
export the key as a ``.p12`` file, let's say ``Certificates.p12``. If Keychain 
asks you for a password to protect this file, just leave it blank. 

For security, you should immediately ``chmod 400 Certificates.p12``, so only
you can read it.

Next, let's use openssl to split that into a PEM cert and a PEM key.

.. code::

    $ openssl pkcs12 -in Certificates.p12 -out ~/.isign/certificate.pem -clcerts -nokeys
    $ openssl pkcs12 -in Certificates.p12 -out ~/.isign/key.pem -nocerts -nodes
    $ chmod 400 ~/.isign/key.pem

Then delete ``Certificates.p12``. 

.. code::

    $ rm Certificates.p12

Finally, download a provisioning profile from the Apple Developer Portal that uses the 
same certificate. Save it as ``~/.isign/isign.mobileprovision``. 

How to use isign
----------------

If you've installed all the files in the proper locations above, then ``isign`` can be now invoked
on any iOS ``.app`` directory, or ``.ipa`` archive, or ``.app.zip`` zipped directory. For example:

.. code::

  $ isign -o resigned.ipa my.ipa
  2015-10-28 16:14:30,548 - isign.app - INFO - archived Ipa to /home/alice/resigned.ipa

You can also call it from Python:

.. code:: python

    from isign import isign
   
    try:
        isign.resign("my.ipa", output_path="resigned.ipa")
    except isign.NotSignable as e:
        print "Not an iOS native app: " + e


isign command line arguments
----------------------------

Synopsis:

.. code::

    isign [-h] [-a <path to applecerts.pem>] 
               [-c <path to your cert in .pem form>]
               [-k <path to your key in .pem form>] 
               [-p <your.mobileprovision>] 
               [-o <output path>]
               <path to app to resign>

**-a <path>, --apple-cert <path>**

Path to Apple certificate in PEM format. This is already included in the library, so you will likely
never need it. In the event that the certificates need to be changed, See the `Apple Certificate documentation <docs/applecerts.rst>`__.

**-c <path>, --certificate <path>**

Path to your certificate in PEM format. Defaults to ``$HOME/.isign/certificate.pem``.

**-h, --help**

Show a help message and exit.

**-k <path>, --key <path>**

Path to your private key in PEM format. Defaults to ``$HOME/.isign/key.pwm``.

**-o <path>, --output <path>**

Path to write the re-signed application. Defaults to ``out`` in your current working directory.

**-p <path>, --provisioning-profile <path>**

Path to your provisioning profile. This should be associated with your certificate. Defaults to 
``$HOME/.isign/isign.mobileprovision``.


Testing
-------

``./run_tests.sh``

Some tests require Apple's
`codesign <https://developer.apple.com/library/mac/documentation/Darwin/Reference/ManPages/man1/codesign.1.html>`__
to run, so they are skipped unless you run them on a Macintosh computer with developer tools.


Packaging
---------

If you were wondering what the ``version.sh`` and ``dev`` was all about, this library is 
packaged according to the Sauce Labs standard for Python packages. For the most part, you don't
have to touch those.


Community contributions
------------------------

Sauce Labs supports ongoing public ``isign`` development. ``isign`` is a part of our infrastructure
for the `iOS Real Device Cloud <https://saucelabs.com/press-room/press-releases/sauce-labs-expands-mobile-test-automation-cloud-with-the-addition-of-real-devices-1>`__,
which allows customers to test apps and websites on real iOS devices. ``isign`` has been successfully re-signing submitted customer apps in production
since June 2015.

Goals for this library include:

* ongoing maintenance as new versions of iOS are released
* speed improvements via parallelization and caching
* better documentation of the data structures involved in code signing (``LC_CODE_SIGNATURE``)
* the thrilling work of code cleanups

Your contributions are valued and welcome. Get in touch with the maintainers, file an issue, or fork the code!

Code of conduct
~~~~~~~~~~~~~~~

This project not have an official code of conduct, yet, but one is forthcoming. Please contribute
to discussion `here <https://github.com/saucelabs/isign/issues/6>`__.


More documentation
------------------

See the `docs <docs>`__ directory of this repository for random stuff that didn't fit here.


Authors
-------
`Neil Kandalgaonkar <https://github.com/neilk>`__ is the main developer and maintainer.

Proof of concept by `Steven Hazel <https://github.com/sah>`__ and Neil Kandalgaonkar.

Reference scripts using Apple tools by `Michael Han <https://github.com/mhan>`__.
