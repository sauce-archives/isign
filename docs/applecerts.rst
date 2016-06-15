Apple certificates
==================

You probably don't need to change this file, not for a long time.

The ``applecerts.pem`` file can be constructed by these steps. In theory
you can export them from Keychain Access, too, but here's a procedure that
doesn't involve an Apple machine. This worked for us in June 2016:

.. code:: bash

        $ curl 'https://www.apple.com/appleca/AppleIncRootCertificate.cer' > AppleIncRootCertificate.cer
        $ curl 'https://developer.apple.com/certificationauthority/AppleWWDRCA.cer' > AppleWWDRCA.cer
        $ openssl x509 -inform der -in AppleIncRootCertificate.cer -outform pem -out AppleIncRootCertificate.pem
        $ openssl x509 -inform der -in AppleWWDRCA.cer -outform pem -out AppleWWDRCA.pem
        $ cat AppleWWDRCA.pem AppleIncRootCertificate.pem > applecerts.pem

Here's a conceptual explanation of what we're doing:

Download the following certs from `Apple's Certificate Authority
Page <https://www.apple.com/certificateauthority/>`__

-  Apple Inc. Root Certificate
-  Worldwide Developer Relations Certificate

Then convert these to
`PEM <http://en.wikipedia.org/wiki/Privacy-enhanced_Electronic_Mail>`__
format.

Then, concatenate them together. This file can now serve as the 'Apple
certificate' for code signing.

