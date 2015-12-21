Installing isign on a Mac
=========================

**Prerequisites**

First, ensure `openssl <https://www.openssl.org>`__ is at version 1.0.1 or better, like
this:

.. code::
  $ openssl version
  OpenSSL 1.0.1 14 Mar 2012

Apple stopped shipping some necessary libraries and headers with OS X 10.11, "El Capitan". 
You can use `homebrew <http://brew.sh>`__ to install them:

.. code::

  $ brew install openssl libffi

You will also have to put ``brew``'s openssl into your path somehow, probably like this:

.. code::

  $ ln -s /usr/local/Cellar/openssl/1.0.2e/bin/openssl /usr/local/bin/openssl

Or, if that bothers you, you can create an environment variable called ``$OPENSSL`` that
points to the right ``openssl``, and ``isign`` will respect that:

.. code::

  $ export OPENSSL=/usr/local/Cellar/openssl/1.0.2e/bin/openssl

And, then you have to add their library and header paths to your environment before
installng ``isign``. The ``brew`` program probably already notified you of this when
you installed. Be careful to use the paths that ``brew`` recommended, but the commands
would look something like this:b

.. code::

  $ export CPPFLAGS=-I/usr/local/opt/openssl/include
  $ export LDFLAGS="-L/usr/local/opt/openssl/lib -L/usr/local/opt/libffi/lib"

Finally, be aware that the ``python`` that ships with Mac OS X doesn't have the package 
manager ``pip``. You can *probably* use ``easy_install`` instead, but the maintainers don't
test that method regularly.

The simplest method is use ``get-pip.py`` 
(see `instructions <http://python-packaging-user-guide.readthedocs.org/en/latest/installing/#install-pip-setuptools-and-wheel>`__
here). Or, you can use ``brew`` and install a better python with ``brew install python``.

Now you are (hopefully) ready to install ``isign``.
