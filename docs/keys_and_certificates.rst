Keys, certificates, and provisioning profiles
============================================

You need a key, certificate, and provisioning profile 
to be able to sign apps. 

Apple tools usually obtain these from your Keychain, or directly from 
Apple's developer site. 

``isign`` requires these be stored on the filesystem, and some of these
files must be in a different format.


Obtain an Apple Developer account
----------------------------------
This is beyond the scope of this documentation for now. However, at the end
of the process, you should have a key and certificate in Keychain, and a 
provisioning profile that you can use to sign apps for one or more of your
own iOS devices.

Make the .isign directory
-------------------------

.. code:: bash
  $ mkdir ~/.isign


Export your key and certificate
--------------------------------

In Keychain Access, open the *Keys*. Find the certificate you use to sign apps 
(it will appear as a "descendant" of your private key). Export
it as a `.p12` file. If Keychain asks you for a password to protect
this file, just leave it blank. This `.p12` file contains both your key and 
your certificate.

Next, let's use openssl to split that into a PEM cert and a PEM key.

.. code:: bash
    $ openssl pkcs12 -in <your>.p12 -out ~/.isign/certificate.pem -clcerts -nokeys
    $ openssl pkcs12 -in <your>.p12 -out ~/.isign/key.pem -nocerts -nodes

Download your provisioning profile
----------------------------------

If you're an Apple developer already, you've probably already created a
provisioning profile that works on one of your iOS devices. Download it from
the Apple Developer Portal, and save it as ``~/.isign/isign.mobileprovision``.



If you don't have an Apple developer account already
====================================================

Account
-------

Obtain an account as an Apple Developer. 

You'll get email from Apple, which will prompt you to set up your
account. Set up passwords and so on as usual.

**Troubleshooting:** you may have to click on the mailed invite link
once to set up your account, and then return to your mail to click on
that invite link again to actually activate your account. Also, in
general, things on the Apple site work better with Safari, so if
something doesn't work, try that browser.

Setting up credentials
----------------------

Your keys and certificates
~~~~~~~~~~~~~~~~~~~~~~~~~~

If you need to create a new key or cert, or change the existing ones we 
are using, here's how.

If you intend to use this account to sign apps for later testing with
Appium, it's important that everything in this account be for
"Developer", not "Distribution". At this moment, Appium uses Instruments
to install apps and otherwise control the phone, and Instruments won't
touch an app that is signed for Distribution. (Incidentally, welcome to
`Richard Stallman's
nightmare <http://www.gnu.org/philosophy/right-to-read.en.html>`__.)

The following procedure works as of June 2015, for adding a new account
from scratch. You will need a Mac to follow these instructions, as
they rely on Apple tools to get you started.

Log into your Apple account.

Go to *Certificates, Identifiers, & Profiles*.

Go to *Certificates > Development* in the left-hand column.

Press the plus icon to add a new certificate.

It will ask what type of certificate you need. If this account is meant
to sign apps for Appium testing, select *iOS App Development*.

It will then instruct you to use Keychain Access to generate a
Certificate Signing Request. In effect you are going to create a
private/public key pair, and then make a little file that says "Hey
Apple, please sign this public key and make a certificate for it, thus
associating both keys with my Apple account!"

Follow the instructions and save that CSR to disk. Press Continue.

Then, the Apple website will ask you to upload that CSR. Do so, and it
will create a certificate for your account in your organization. This
certificate might need to be approved by an admin before you can
download it.

Once it's approved, download it!

It will probably be named something generic like
``ios_development.cer``, so rename it to something more meaningful and
put it somewhere safe.

Import that .cer into Keychain. Keychain will detect that it has an
associated private key, and in views where you see keys, the certificate
will be "inside" the key, and vice versa.

Finally, let's export these.

In Keychain Access, open the *Keys*. Find the private key you created and export
it as a `.p12` file. If Keychain asks you for a password to protect
this file, just leave it blank. This `.p12` file contains both your key and 
your certificate.

Next, let's use openssl to split that into a PEM cert and a PEM key. 

.. code:: bash

        $ openssl pkcs12 -in <your>.p12 -out <your>.cert.pem -clcerts -nokeys
        $ openssl pkcs12 -in <your>.p12 -out <your>.key.pem -nocerts -nodes

These files can now be used for code signing. Respectively, you can use them
as the `signer_key_file` and `signer_cert_file` arguments to `isign.resign()`,
or, on the command line, the `-k` and `-c` arguments.

Provisioning profile
~~~~~~~~~~~~~~~~~~~~

One more hoop to jump through. Apple will allow you to sign an app, but
it will only work on a number of devices which have been registered with
Apple. We will be registering each of those devices as we deploy them.
For the moment, our development iOS devices are also in the same pool.

We just need to tell Apple that your user is allowed to deploy on those
devices. The file that proves this is called a provisioning profile.

In the Developer portal, go to *Provisioning Profiles*, and create a new
development profile. (You can modify an old one, but it's painful -- the
existing versions of the profile expire or something.)

In *Select App ID*, use 'iOS RDC' -- I think anything with our Apple
organizational unit plus dot-star works (``JWKXD469L2.\*``)

Next, in 'Select certificates', select the certificates you want, which
probably includes the you care about.

Putting credentials into Ansible
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

See `deploy.rst <deploy.rst>`__.
