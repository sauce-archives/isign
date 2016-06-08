isign
=====

A tool and library to re-sign iOS applications, without proprietary Apple software.

For example, an iOS app in development would probably only run on the developer's iPhone. 
``isign`` can alter the app so that it can run on another developer's iPhone.

Apple tools already exist to do this. But with ``isign``, now you can do this on operating
systems like Linux.


Table of contents
-----------------

- `Installing`_
- `How to get started`_
- `How to use isign`_
- `isign command line arguments`_
- `Contributing`_
- `More documentation`_
- `Authors`_


.. _Installing:

Installing
----------

Linux
~~~~~

The latest version of ``isign`` can be installed via `PyPi <https://pypi.python.org/pypi/isign/>`__:

.. code::

  $ pip install isign

Mac OS X
~~~~~~~~

On Mac OS X, there are a lot of prerequisites, so the ``pip`` method probably won't work.
The easiest method is to use ``git`` to clone the `source code repository <https://github.com/saucelabs/isign>`__ and 
run the install script:

.. code::

  $ git clone https://github.com/saucelabs/isign.git
  $ cd isign
  $ sudo ./INSTALL.sh

.. _How to get started:

How to get started
------------------

All the libraries and tools that ``isign`` needs to run will work on both Linux 
and Mac OS X. However, you will need a Mac to export your Apple developer 
credentials. 

If you're like most iOS developers, credentials are confusing -- if so check out 
the `documentation on credentials <https://github.com/saucelabs/isign/blob/master/docs/credentials.rst>`__ on Github.

You should have a key and certificate in 
`Keychain Access <https://en.wikipedia.org/wiki/Keychain_(software)>`__,
and a provisioning profile associated with that certificate, that you 
can use to sign iOS apps for one or more of your own iOS devices.

In Keychain Access, open the *Certificates*. Find the certificate you use to sign apps. 
Right click on it and export the key as a ``.p12`` file, let's say ``Certificates.p12``. If Keychain 
asks you for a password to protect this file, just leave it blank. 

Next, let's extract the key and certificate you need, into a standard PEM format.

.. code::

  $ isign_export_creds.sh ~/Certificates.p12

If you get prompted for a password, just press ``Return``.

By default, ``isign_export_creds.sh`` will put these files into ``~/.isign``, which is
the standard place to put ``isign`` configuration files.

Finally, you need a provisioning profile from the Apple Developer Portal that uses
the same certificate. If you've never dealt with this, the provisioning profile is 
what tells the phone that you Apple has okayed you installing apps onto this particular phone.

If you develop with XCode, you might have a provisioning profile already. 
On the Mac where you develop with XCode, try running the ``isign_guess_mobileprovision.sh`` script. 
If you typically have only a few provisioning profiles and install on one phone, it might find it. 

Anyway, once you have a ``.mobileprovision`` file, move it to ``~/.isign/isign.mobileprovision``.

The end result should look like this:

.. code::

  $ ls -l ~/.isign
  -r--r--r--    1 alice  staff  2377 Sep  4 14:17 certificate.pem
  -r--r--r--    1 alice  staff  9770 Nov 23 13:30 isign.mobileprovision
  -r--------    1 alice  staff  1846 Sep  4 14:17 key.pem

And now you're ready to start re-signing apps!

.. _How to use isign:

How to use isign
----------------

If you've installed all the files in the proper locations above, then ``isign`` can be now invoked
on any iOS ``.app`` directory, or ``.ipa`` archive, or ``.app.zip`` zipped directory. For example:

.. code::

  $ isign -o resigned.ipa my.ipa
  archived Ipa to /home/alice/resigned.ipa

You can also call it from Python:

.. code:: python

  from isign import isign

  isign.resign("my.ipa", output_path="resigned.ipa")

.. _isign command line arguments:

isign command line arguments
----------------------------

.. code::

  # Resigning by specifying all credentials, input file, and output file
  $ isign -c /path/to/mycert.pem -k ~/mykey.pem -p path/to/my.mobileprovision \
          -o resigned.ipa original.ipa

  # Resigning, with credentials under default filenames in ~/.isign - less to type!
  $ isign -o resigned.ipa original.ipa

  # Modify Info.plist properties in resigned app
  $ isign -i CFBundleIdentifier=com.example.myapp,CFBundleName=MyApp -o resigned.ipa original.ipa

  # Get help
  $ isign -h

**-a <path>, --apple-cert <path>**

Path to Apple certificate in PEM format. This is already included in the library, so you will likely
never need it. In the event that the certificates need to be changed, See the `Apple Certificate documentation <docs/applecerts.rst>`__.

**-c <path>, --certificate <path>**

Path to your certificate in PEM format. Defaults to ``$HOME/.isign/certificate.pem``.

**-h, --help**

Show a help message and exit.

**-i, --info**

While resigning, add or update info in the application's information property list (Info.plist). 
Takes a comma-separated list of key=value pairs, such as 
``CFBundleIdentifier=com.example.app,CFBundleName=ExampleApp``. Use with caution!
See Apple documentation for `valid Info.plist keys <https://developer.apple.com/library/ios/documentation/General/Reference/InfoPlistKeyReference/Introduction/Introduction.html>`_.

**-k <path>, --key <path>**

Path to your private key in PEM format. Defaults to ``$HOME/.isign/key.pwm``.

**-o <path>, --output <path>**

Path to write the re-signed application. Defaults to ``out`` in your current working directory.

**-p <path>, --provisioning-profile <path>**

Path to your provisioning profile. This should be associated with your certificate. Defaults to 
``$HOME/.isign/isign.mobileprovision``.


.. _Contributing:

Contributing
------------

Development happens on `our Github repository <https://github.com/saucelabs/isign>`__. File an issue, or fork the code!

You'll probably want to create some kind of python virtualenv, so you don't have to touch your system python or its 
libraries. `virtualenvwrapper <https://virtualenvwrapper.readthedocs.org/en/latest/>`__ is a good tool for this.

Then, just do the following:

.. code::

  $ git clone https://github.com/saucelabs/isign.git
  $ cd isign
  $ dev/setup.sh 
  $ ./run_tests.sh

If the tests don't pass please `file an issue <https://github.com/saucelabs/isign/issues>`__. Please keep the tests up to date as you develop.

Note: some tests require Apple's
`codesign <https://developer.apple.com/library/mac/documentation/Darwin/Reference/ManPages/man1/codesign.1.html>`__
to run, so they are skipped unless you run them on a Macintosh computer with developer tools.

Okay, if all the tests passed, you now have an 'editable' install of isign. Any edits to this repo will affect (for instance)
how the `isign` command line tool works.

Sauce Labs supports ongoing public ``isign`` development. ``isign`` is a part of our infrastructure
for the `iOS Real Device Cloud <https://saucelabs.com/press-room/press-releases/sauce-labs-expands-mobile-test-automation-cloud-with-the-addition-of-real-devices-1>`__,
which allows customers to test apps and websites on real iOS devices. ``isign`` has been successfully re-signing submitted customer apps in production
since June 2015.

This project not have an official code of conduct, yet, but one is forthcoming. Please contribute
to discussion `here <https://github.com/saucelabs/isign/issues/6>`__.

.. _More documentation:

More documentation
------------------

See the `docs <docs>`__ directory of this repository for random stuff that didn't fit here.

.. _Authors:


Authors
-------

`Neil Kandalgaonkar <https://github.com/neilk>`__ is the main developer and maintainer.

Proof of concept by `Steven Hazel <https://github.com/sah>`__ and Neil Kandalgaonkar.

Reference scripts using Apple tools by `Michael Han <https://github.com/mhan>`__.
