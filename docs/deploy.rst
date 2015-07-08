Deploying code
~~~~~~~~~~~~~~

This repo has a webhook to tell our Jenkins server to publish a pip-compatible
package to our `continuous integration server <https://ci.saucelabs.net/artifacts/dist-release/>`__ as well as S3.

See the `Sauce Dev Python Packaging` <https://saucedev.atlassian.net/wiki/display/AD/Python+packaging>`__ docs for more.

Deploying keys, certificates, and profiles
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As of July 2015, we manage all these with Ansible, in the sauce-ansible repo.

There are different credentials for each environment (development, build test, production)
These credentials are in files called ``isign-creds``, located in different directories.

The credentials are all Vault-encrypted together into a single YAML file like, with
the following keys and values. n.b. for historical reasons, the keys always begin 
with ``mobdev_``, even if it's for build or production.

``mobdev_cert_pem``: certificate in PEM format

``mobdev_key_pem``: key in PEM format

``mobdev1_mobileprovision_base64``: .mobileprovision file converted to base64, wrapped
with a short line length, like 62 characters. The following commands should work.

.. code:: bash

        Mac OS X:
        $ base64 -b 62 <your.mobileprovision>

        Linux: 
        $ base64 -w 62 <your.mobileprovision>
