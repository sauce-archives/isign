#!/usr/bin/env python

import app
import argparse
import logging
from log_to_stderr import log_to_stderr
# import makesig
import os
import os.path
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


log = logging.getLogger(__name__)


def resign(input_path,
           certificate=CERTIFICATE_PATH,
           key=KEY_PATH,
           apple_cert=APPLE_CERT_PATH,
           provisioning_profile=PROVISIONING_PROFILE_PATH,
           output_path=join(os.getcwd(), "out")):
    """ simply for convenience, and to omit default args """
    return app.resign(input_path,
                      certificate,
                      key,
                      apple_cert,
                      provisioning_profile,
                      output_path)


# The rest is all about parsing command line args
# could be moved to a different 'binary'

def absolute_path_argument(path):
    return os.path.abspath(os.path.expanduser(path))


def parse_args():
    # note that for arguments which eventually get fed into
    # isign.resign, we deliberately don't set defaults. The kwarg
    # defaults in isign.resign will be used
    parser = argparse.ArgumentParser(
        description='Resign an iOS application with a new identity '
                    'and provisioning profile.')
    parser.add_argument(
        '-p', '--provisioning-profile',
        dest='provisioning_profile',
        required=False,
        metavar='<your.mobileprovision path>',
        type=absolute_path_argument,
        help='Path to provisioning profile'
    )
    parser.add_argument(
        '-a', '--apple-cert',
        dest='apple_cert',
        required=False,
        metavar='<apple cert>',
        type=absolute_path_argument,
        help='Path to Apple certificate in .pem form'
    )
    parser.add_argument(
        '-k', '--key',
        dest='key',
        required=False,
        metavar='<key path>',
        type=absolute_path_argument,
        help='Path to your organization\'s key in .p12 format'
    )
    parser.add_argument(
        '-c', '--certificate',
        dest='certificate',
        required=False,
        metavar='<certificate path>',
        type=absolute_path_argument,
        help='Path to your organization\'s certificate in .pem form'
    )
    parser.add_argument(
        '-o', '--output',
        dest='output_path',
        required=False,
        metavar='<output path>',
        type=absolute_path_argument,
        help='Path to output file or directory'
    )
    parser.add_argument(
        'app_paths',
        nargs=1,
        metavar='<app path>',
        type=absolute_path_argument,
        help='Path to application to re-sign, typically a '
             'directory ending in .app or file ending in .ipa.'
    )
    parser.add_argument(
        '-v', '--verbose',
        dest='verbose',
        action='store_true',
        default=False,
        required=False,
        help='Set logging level to debug.'
    )

    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()

    if args.verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
    log_to_stderr(level)

    # Filter out args that don't matter to the
    # resign call, like verbosity or help
    resign_args = ['certificate',
                   'key',
                   'apple_cert',
                   'provisioning_profile',
                   'output_path']
    kwargs = {}
    # we want the unused command line args to be
    # missing in kwargs, so the defaults are used
    for k, v in vars(args).iteritems():
        if k in resign_args and v is not None:
            kwargs[k] = v

    resign(args.app_paths[0], **kwargs)
