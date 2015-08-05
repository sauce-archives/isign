import app
# import makesig
import os
from os.path import dirname, join, realpath

# this comes with the repo
PACKAGE_ROOT = dirname(realpath(__file__))
APPLE_CERT_PATH = join(PACKAGE_ROOT, 'apple_credentials', 'applecerts.pem')

# should be deployed with Ansible (as of July 2015, the playbook is isign.yml)
DEFAULT_CREDENTIALS_PATH = join(os.environ['HOME'], 'isign-credentials')
CERTIFICATE_PATH = join(DEFAULT_CREDENTIALS_PATH, 'mobdev.cert.pem')
KEY_PATH = join(DEFAULT_CREDENTIALS_PATH, 'mobdev.key.pem')
PROVISIONING_PROFILE_PATH = join(DEFAULT_CREDENTIALS_PATH,
                                 'mobdev1.mobileprovision')


class NotSignable(Exception):
    """ This is just so we don't expose isign.app.NotSignable """
    pass


def resign(input_path,
           certificate=CERTIFICATE_PATH,
           key=KEY_PATH,
           apple_cert=APPLE_CERT_PATH,
           provisioning_profile=PROVISIONING_PROFILE_PATH,
           output_path=join(os.getcwd(), "out")):
    """ simply for convenience, and to omit default args """
    try:
        return app.resign(input_path,
                          certificate,
                          key,
                          apple_cert,
                          provisioning_profile,
                          output_path)
    except app.NotSignable as e:
        # re-raise the exception without exposing internal
        # details of how it happened
        raise NotSignable(e)
