import archive
# import makesig
import exceptions
import os
from os.path import dirname, exists, join, realpath

# this comes with the repo
PACKAGE_ROOT = dirname(realpath(__file__))
APPLE_CERT_PATH = join(PACKAGE_ROOT, 'apple_credentials', 'applecerts.pem')

# We will default to using credentials if they are located in a particular
# directory. Sauce Labs in 2015 uses a scheme under '~/isign-credentials'
# but probably everyone else should use '~/.isign', or specify credential
# files in command line arguments.
if exists(join(os.environ['HOME'], 'isign-credentials')):
    DEFAULT_CREDENTIALS_PATH = join(os.environ['HOME'], 'isign-credentials')
    CERTIFICATE_PATH = join(DEFAULT_CREDENTIALS_PATH, 'mobdev.cert.pem')
    KEY_PATH = join(DEFAULT_CREDENTIALS_PATH, 'mobdev.key.pem')
    PROVISIONING_PROFILE_PATH = join(DEFAULT_CREDENTIALS_PATH,
                                     'mobdev1.mobileprovision')
else:
    DEFAULT_CREDENTIALS_PATH = join(os.environ['HOME'], '.isign')
    CERTIFICATE_PATH = join(DEFAULT_CREDENTIALS_PATH, 'certificate.pem')
    KEY_PATH = join(DEFAULT_CREDENTIALS_PATH, 'key.pem')
    PROVISIONING_PROFILE_PATH = join(DEFAULT_CREDENTIALS_PATH,
                                     'isign.mobileprovision')


class NotSignable(Exception):
    """ This is just so we don't expose other sorts of exceptions """
    pass


def resign(input_path,
           certificate=CERTIFICATE_PATH,
           key=KEY_PATH,
           apple_cert=APPLE_CERT_PATH,
           provisioning_profile=PROVISIONING_PROFILE_PATH,
           output_path=join(os.getcwd(), "out"),
           info_props=None):
    """ simply for convenience, and to omit default args """
    try:
        return archive.resign(input_path,
                              certificate,
                              key,
                              apple_cert,
                              provisioning_profile,
                              output_path,
                              info_props)
    except exceptions.NotSignable as e:
        # re-raise the exception without exposing internal
        # details of how it happened
        raise NotSignable(e)
