#!/usr/bin/env python

import argparse
import distutils
# import makesig
from signer import Signer
import os
import os.path
import shutil
from subprocess import call
from app import App, IpaApp

UNZIP_BIN = distutils.spawn.find_executable('unzip')


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
            required=True,
            metavar='<your.mobileprovision>',
            type=exists_absolute_path_argument,
            help='Path to provisioning profile')
    parser.add_argument(
            '-a', '--apple-cert',
            dest='apple_cert',
            required=True,
            metavar='<path>',
            type=exists_absolute_path_argument,
            help='Path to Apple certificate in .pem form')
    parser.add_argument(
            '-k', '--key',
            dest='key',
            required=True,
            metavar='<path>',
            type=exists_absolute_path_argument,
            help='Path to your organization\'s key in .p12 format')
    parser.add_argument(
            '-c', '--certificate',
            dest='certificate',
            required=True,
            metavar='<certificate>',
            type=exists_absolute_path_argument,
            help='Path to your organization\'s certificate in .pem form')
    parser.add_argument(
            '-s', '--staging',
            dest='stage_dir',
            required=False,
            metavar='<path>',
            type=absolute_path_argument,
            default=None,
            help='Path to stage directory.')
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
           certificate,
           key,
           apple_cert,
           provisioning_profile,
           stage_dir=os.path.join(os.getcwd(), 'stage'),
           output_path=os.path.join(os.getcwd(), 'out')):
    """ resigns the app, returns path to new app """

    signer = Signer(signer_cert_file=certificate,
                    signer_key_file=key,
                    apple_cert_file=apple_cert)

    if os.path.exists(stage_dir):
        shutil.rmtree(stage_dir)
    os.mkdir(stage_dir)

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
    # the signature for resign()
    for key in ['stage_dir', 'output_path']:
        if key in args_dict and args_dict[key] is None:
            del args_dict[key]

    output_path = resign(**args_dict)

    print "Re-signed package: {0}".format(output_path)
