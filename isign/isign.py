#!/usr/bin/env python

import app as application
import argparse
import logging
from log_to_stderr import log_to_stderr
# import makesig
import os
import os.path
from os.path import dirname, join, realpath
from signer import Signer
import sys


# this comes with the repo
PACKAGE_ROOT = dirname(realpath(__file__))
APPLE_CERT_PATH = join(PACKAGE_ROOT, 'apple_credentials', 'applecerts.pem')

# should be deployed with a fab task (as of June 2015, it's ios_rdc_creds)
DEFAULT_CREDENTIALS_PATH = join(os.environ['HOME'], 'isign-credentials')
CERTIFICATE_PATH = join(DEFAULT_CREDENTIALS_PATH, 'mobdev.cert.pem')
KEY_PATH = join(DEFAULT_CREDENTIALS_PATH, 'mobdev.key.pem')
PROVISIONING_PROFILE_PATH = join(DEFAULT_CREDENTIALS_PATH,
                                 'mobdev1.mobileprovision')


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def absolute_path_argument(path):
    return os.path.abspath(os.path.expanduser(path))


def exists_absolute_path_argument(path):
    path = absolute_path_argument(path)
    if not os.path.exists(path):
        raise argparse.ArgumentTypeError("%s does not exist!" % path)
    return path


def parse_args():
    parser = argparse.ArgumentParser(
            description='Resign an iOS application with a new identity '
                        'and provisioning profile.')
    parser.add_argument(
            '-p', '--provisioning-profile',
            dest='provisioning_profile',
            required=False,
            metavar='<your.mobileprovision path>',
            type=exists_absolute_path_argument,
            help='Path to provisioning profile')
    parser.add_argument(
            '-a', '--apple-cert',
            dest='apple_cert',
            required=False,
            metavar='<apple cert>',
            type=exists_absolute_path_argument,
            help='Path to Apple certificate in .pem form')
    parser.add_argument(
            '-k', '--key',
            dest='key',
            required=False,
            metavar='<key path>',
            type=exists_absolute_path_argument,
            help='Path to your organization\'s key in .p12 format')
    parser.add_argument(
            '-c', '--certificate',
            dest='certificate',
            required=False,
            metavar='<certificate path>',
            type=exists_absolute_path_argument,
            help='Path to your organization\'s certificate in .pem form')
    parser.add_argument(
            '-o', '--output',
            dest='output_path',
            required=False,
            metavar='<output path>',
            type=absolute_path_argument,
            default=None,
            help='Path to output file or directory')
    parser.add_argument(
            'app_paths',
            nargs=1,
            metavar='<app path>',
            type=exists_absolute_path_argument,
            help='Path to application to re-sign, typically a '
                 'directory ending in .app or file ending in .ipa.')
    return parser.parse_args()


class NotSignable(Exception):
    pass


def new_from_archive(path):
    try:
        app = application.new_from_archive(path)
    except (application.NotMatched, application.NotNative) as e:
        log.debug(e)
        raise NotSignable(e)
    return app


def resign(app,
           certificate=CERTIFICATE_PATH,
           key=KEY_PATH,
           apple_cert=APPLE_CERT_PATH,
           provisioning_profile=PROVISIONING_PROFILE_PATH,
           output_path=os.path.join(os.getcwd(), 'out')):
    """ Given app object, returns path of newly resigned app """

    signer = Signer(signer_cert_file=certificate,
                    signer_key_file=key,
                    apple_cert_file=apple_cert)

    app.provision(provisioning_profile)
    app.create_entitlements(signer.team_id)
    app.sign(signer)
    app.package(output_path)
    log.info("Created resigned app at <%s>", output_path)

    return output_path


if __name__ == '__main__':
    log_to_stderr(log)

    args = parse_args()
    args_dict = vars(args)
    args_dict['input_path'] = args.app_paths[0]
    del args_dict['app_paths']

    # make sure defaults are triggered properly in
    # the signature for resign() -- rather than a value of None,
    # they should be absent
    for key in args_dict.keys():
        if key in args_dict and args_dict[key] is None:
            del args_dict[key]

    input_path = args_dict['input_path']
    del args_dict['input_path']

    try:
        with new_from_archive(input_path) as app:
            resign(app, **args_dict)
    except NotSignable, e:
        log.debug("Can't sign <{0}>: {1}\n".format(input_path, e))
        sys.exit(1)
