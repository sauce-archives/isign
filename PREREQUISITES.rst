Prerequisites
=============

For Linux or Mac platforms, the ``INSTALL.sh`` script should take care of 
everything you need.  

If you don't want to run that script on the machine where you want to re-sign apps, 
this will explain what you need.

First, on the machine where you're going to re-sign apps, ensure 
`openssl <https://www.openssl.org>`__ is at version 1.0.1 or better, like
this:

.. code::

  $ openssl version
  OpenSSL 1.0.1 14 Mar 2012

If that looks okay, you can probably install. If not:

.. _Linux:

Linux
~~~~~

You can probably easily update this with your package manager, such as 
``apt-get upgrade openssl``.

.. _Mac OS X:

Mac OS X
~~~~~~~~

With OS X 10.11 "El Capitan", Apple stopped shipping some programs, libraries, and 
headers that we'll need. You can use `homebrew <http://brew.sh>`__ to install them:

.. code::

  $ brew install openssl libffi

You will also have to put ``brew``'s openssl into your path somehow, probably like this:

.. code::
  
  $ brew list openssl
  ... 
  /usr/local/Cellar/openssl/1.0.2e/bin/openssl    <-- you want this
  ...

  $ ln -s /usr/local/Cellar/openssl/1.0.2e/bin/openssl /usr/local/bin/openssl

If you really don't want to alter the default ``openssl``, you can put the path to brew's 
``openssl`` in an environment variable, ``$OPENSSL``, e.g.

.. code::

  $ export OPENSSL=/usr/local/Cellar/openssl/1.0.2e/bin/openssl 

If ``isign`` sees that, it will use that for its ``openssl`` instead.

Anyway, no matter how you install the binary, to complete the installation of ``isign``
you need to add some library paths to your environment. The procedure will 
look something like this.

.. code::
  
  $ brew info openssl
  ...
  build variables:

    LDFLAGS:  -L/usr/local/opt/openssl/lib
    CPPFLAGS: -I/usr/local/opt/openssl/include

  $ brew info libffi
  ...
  build variables:

    LDFLAGS:  -L/usr/local/opt/libffi/lib

Then, take the flags from above, and put them into appropriate environment
variables:

.. code::

  $ export LDFLAGS="-L/usr/local/opt/openssl/lib -L/usr/local/opt/libffi/lib"
  $ export CPPFLAGS="-I/usr/local/opt/openssl/include"

Finally, be aware that the ``python`` that ships with Mac OS X doesn't have the package 
manager ``pip``. You can probably use ``easy_install`` instead of ``pip``. Or, you can get a more
up-to-date python with ``brew install python``.

Now you're probably ready to install ``isign``. A simple ``pip install isign`` should succeed.
