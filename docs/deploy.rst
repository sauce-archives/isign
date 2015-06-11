Deploying keys, certs, and profiles
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We use ansible-vault to store these securely, under the `isign_creds`
role, in the repo `sauce-ansible`.


Deploying code
~~~~~~~~~~~~~~

This repo has a webhook to tell our Jenkins server to publish a pip-compatible
package to our `continuous integration server <https://ci.saucelabs.net/artifacts/dist-release/>`__ as well as S3.

See the `Sauce Dev Python Packaging` <https://saucedev.atlassian.net/wiki/display/AD/Python+packaging>`__ docs for more.
