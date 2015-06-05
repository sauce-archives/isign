#!/usr/bin/env python

from app import App, IpaApp
import argparse
import distutils
# import makesig
from signer import Signer
import os
import os.path
from os.path import dirname, join, realpath
import shutil
from subprocess import call
import tempfile

UNZIP_BIN = distutils.spawn.find_executable('unzip')

# this comes with the repo
REPO_ROOT = dirname(dirname(realpath(__file__)))
APPLE_CERT_PATH = join(REPO_ROOT, 'apple_credentials', 'applecerts.pem')

# should be deployed with a fab task (as of June 2015, it's ios_rdc_creds)
DEFAULT_CREDENTIALS_PATH = join(os.environ['HOME'], 'iresign-credentials')
CERTIFICATE_PATH = join(DEFAULT_CREDENTIALS_PATH, 'mobdev.pem')
KEY_PATH = join(DEFAULT_CREDENTIALS_PATH, 'mobdev.p12')
PROVISIONING_PROFILE_PATH = join(DEFAULT_CREDENTIALS_PATH,
                                 'mobdev1.mobileprovision')


def absolute_path_argument(path):
    return os.path.abspath(os.path.expanduser(path))


def exists_absolute_path_argument(path):
    path = absolute_path_argument(path)
    if not os.path.exists(path):
        raise argparse.ArgumentTypeError("%s does not exist!" % path)
    return path


def app_argument(path):
    path = exists_absolute_path_argument(path)
    _, extension = os.path.splitext(path)
    if not(extension == '.app' or extension == '.ipa'):
        raise argparse.ArgumentTypeError(
                "{0} doesn't seem to be an .app or .ipa".format(path))
    return path


def parse_args():
    parser = argparse.ArgumentParser(
            description='Resign an iOS application with a new identity '
                        'and provisioning profile.')
    parser.add_argument(
            '-p', '--provisioning-profile',
            dest='provisioning_profile',
            required=False,
            metavar='<your.mobileprovision>',
            type=exists_absolute_path_argument,
            help='Path to provisioning profile')
    parser.add_argument(
            '-a', '--apple-cert',
            dest='apple_cert',
            required=False,
            metavar='<path>',
            type=exists_absolute_path_argument,
            help='Path to Apple certificate in .pem form')
    parser.add_argument(
            '-k', '--key',
            dest='key',
            required=False,
            metavar='<path>',
            type=exists_absolute_path_argument,
            help='Path to your organization\'s key in .p12 format')
    parser.add_argument(
            '-c', '--certificate',
            dest='certificate',
            required=False,
            metavar='<certificate>',
            type=exists_absolute_path_argument,
            help='Path to your organization\'s certificate in .pem form')
    parser.add_argument(
            '-o', '--output',
            dest='output_path',
            required=False,
            metavar='<path>',
            type=absolute_path_argument,
            default=None,
            help='Path to output file or directory')
    parser.add_argument(
            'app',
            nargs=1,
            metavar='<path>',
            type=app_argument,
            help='Path to application to re-sign, typically a '
                 'directory ending in .app or file ending in .ipa.')
    return parser.parse_args()


def unpack_received_app(path, unpack_dir):
    _, extension = os.path.splitext(path)
    if extension == '.app':
        app_name = os.path.basename(path)
        target_dir = os.path.join(unpack_dir, app_name)
        shutil.copytree(path, target_dir)
        app = App(target_dir)
    elif extension == '.ipa':
        call([UNZIP_BIN, "-qu", path, "-d", unpack_dir])
        app = IpaApp(unpack_dir)
    else:
        # should be impossible
        raise Exception("unrecognized extension: {0}".format(path))
    return app


def resign(app,
           certificate=CERTIFICATE_PATH,
           key=KEY_PATH,
           apple_cert=APPLE_CERT_PATH,
           provisioning_profile=PROVISIONING_PROFILE_PATH,
           output_path=os.path.join(os.getcwd(), 'out')):
    """ resigns the app, returns path to new app """

    signer = Signer(signer_cert_file=certificate,
                    signer_key_file=key,
                    apple_cert_file=apple_cert)

    stage_dir = tempfile.mkdtemp(prefix="iresign-stage")

    app = unpack_received_app(app, stage_dir)
    app.provision(provisioning_profile)
    app.create_entitlements(signer.team_id)
    app.sign(signer)
    actual_output_path = app.package(output_path)

    shutil.rmtree(stage_dir)

    return actual_output_path


if __name__ == '__main__':
    args = parse_args()
    args_dict = vars(args)
    args_dict['app'] = args.app[0]

    # make sure defaults are triggered properly in
    # the signature for resign() -- rather than a value of None,
    # they should be absent
    for key in args_dict.keys():
        if key in args_dict and args_dict[key] is None:
            del args_dict[key]

    output_path = resign(**args_dict)

    print "Re-signed package: {0}".format(output_path)
