#!/usr/bin/env python

import argparse
import biplist
import code_resources
import distutils
import glob
# import makesig
from signer import Signer
import os
import os.path
import shutil
import signable
from subprocess import call

ZIP_BIN = distutils.spawn.find_executable('zip')
UNZIP_BIN = distutils.spawn.find_executable('unzip')

# Sauce Labs Apple Organizational Unit
TEAM_ID = 'JWKXD469L2'


class App(object):
    def __init__(self, path):
        self.path = path
        self.entitlements_path = os.path.join(self.path,
                                              'Entitlements.plist')
        self.app_dir = self.get_app_dir()
        self.provision_path = os.path.join(self.app_dir,
                                           'embedded.mobileprovision')

        # will be added later
        self.seal_path = None

        info_path = os.path.join(self.get_app_dir(), 'Info.plist')
        if not os.path.exists(info_path):
            raise Exception('no Info.plist at {0}'.format(info_path))
        self.info = biplist.readPlist(info_path)

    def get_app_dir(self):
        return self.path

    def get_executable_path(self):
        executable_name = None
        if 'CFBundleExecutable' in self.info:
            executable_name = self.info['CFBundleExecutable']
        else:
            basename = os.path.basename(self.app_dir)
            executable_name, _ = os.path.splitext(basename)
        executable = os.path.join(self.app_dir, executable_name)
        if not os.path.exists(executable):
            raise Exception(
                    'could not find executable for {0}'.format(self.path))
        return executable

    def provision(self, provision_path):
        shutil.copyfile(provision_path, self.provision_path)

    def create_entitlements(self):
        entitlements = {
            "keychain-access-groups": [TEAM_ID + '.*'],
            "com.apple.developer.team-identifier": TEAM_ID,
            "application-identifier": TEAM_ID + '.*',
            "get-task-allow": True
        }
        biplist.writePlist(entitlements, self.entitlements_path, binary=False)
        print "wrote Entitlements to {0}".format(self.entitlements_path)

    def sign_dylib(self, path, signer):
        dylib = signable.Dylib(self, path)
        dylib.sign(signer)

    def sign(self, signer):
        # first sign all the dylibs
        frameworks_path = os.path.join(self.app_dir, 'Frameworks')
        if os.path.exists(frameworks_path):
            dylib_paths = glob.glob(os.path.join(frameworks_path, '*.dylib'))
            for dylib_path in dylib_paths:
                self.sign_dylib(dylib_path, signer)
        # then create the seal
        # TODO maybe the app should know what its seal path should be...
        self.seal_path = code_resources.make_seal(self.get_executable_path(),
                                                  self.get_app_dir())
        # then sign the app
        executable = signable.Executable(self, self.get_executable_path())
        executable.sign(signer)

    def package(self, output_path):
        if not output_path.endswith('.app'):
            output_path = output_path + '.app'
        os.rename(self.app_dir, output_path)
        return output_path


class IpaApp(App):
    def _get_payload_dir(self):
        return os.path.join(self.path, "Payload")

    def get_app_dir(self):
        glob_path = os.path.join(self._get_payload_dir(), '*.app')
        apps = glob.glob(glob_path)
        count = len(apps)
        if count != 1:
            err = "Expected 1 app in {0}, found {1}".format(glob_path, count)
            raise Exception(err)
        return apps[0]

    def package(self, output_path):
        if not output_path.endswith('.ipa'):
            output_path = output_path + '.ipa'
        temp = "out.ipa"
        # need to chdir and use relative paths, because zip is stupid
        old_cwd = os.getcwd()
        os.chdir(self.path)
        relative_payload_path = os.path.relpath(self._get_payload_dir(),
                                                self.path)
        call([ZIP_BIN, "-qr", temp, relative_payload_path])
        os.rename(temp, output_path)
        os.chdir(old_cwd)
        return output_path

    def sign_dylib(self, path, signer):
        dylib = signable.IpaDylib(self, path)
        dylib.sign(signer)


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
            default=os.path.join(os.getcwd(), 'stage'),
            help='Path to stage directory.')
    parser.add_argument(
            '-o', '--output',
            dest='output_path',
            required=False,
            metavar='<path>',
            type=absolute_path_argument,
            default=os.path.join(os.getcwd(), 'out'),
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


if __name__ == '__main__':
    args = parse_args()

    received_app_path = args.app[0]

    signer = Signer(signer_cert_file=args.certificate,
                    signer_key_file=args.key,
                    apple_cert_file=args.apple_cert,
                    team_id=TEAM_ID)

    if os.path.exists(args.stage_dir):
        shutil.rmtree(args.stage_dir)
    os.mkdir(args.stage_dir)

    app = unpack_received_app(received_app_path, args.stage_dir)
    app.provision(args.provisioning_profile)
    app.create_entitlements()
    app.sign(signer)
    output_path = app.package(args.output_path)

    if os.path.exists(args.stage_dir):
        shutil.rmtree(args.stage_dir)

    print "Re-signed package: {0}".format(output_path)
