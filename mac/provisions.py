#!/usr/bin/env python

# Port of @mikehan's provisions.sh

import argparse
import glob
import os
import os.path
import shutil
from subprocess import call, Popen
import tempfile

CODESIGN_BIN = '/usr/bin/codesign'
PLIST_BUDDY_BIN = '/usr/libexec/PlistBuddy'
SECURITY_BIN = '/usr/bin/security'
ZIP_BIN = '/usr/bin/zip'
UNZIP_BIN = '/usr/bin/unzip'


class ReceivedApp(object):
    def __init__(self, path):
        self.path = path

    def unpack_to_dir(self, unpack_dir):
        app_name = os.path.basename(self.path)
        target_dir = os.path.join(unpack_dir, app_name)
        shutil.copytree(self.path, target_dir)
        return App(target_dir)


class ReceivedIpaApp(ReceivedApp):
    def unpack_to_dir(self, target_dir):
        call([UNZIP_BIN, "-qu", self.path, "-d", target_dir])
        return IpaApp(target_dir)


class App(object):
    def __init__(self, path):
        self.path = path
        self.entitlements_path = os.path.join(self.path,
                                              'Entitlements.plist')
        self.app_dir = self.get_app_dir()
        self.provision_path = os.path.join(self.app_dir,
                                           'embedded.mobileprovision')

    def get_app_dir(self):
        return self.path

    def provision(self, provision_path):
        print "provision_path: {0}".format(provision_path)
        shutil.copyfile(provision_path, self.provision_path)

    def create_entitlements(self):
        # we decode part of the provision path, then extract the
        # Entitlements part, then write that to a file in the app.

        # piping to Plistbuddy doesn't seem to work :(
        # hence, temporary intermediate file

        decoded_provision_fh, decoded_provision_path = tempfile.mkstemp()
        decoded_provision_fh = open(decoded_provision_path, 'w')
        decode_args = [SECURITY_BIN, 'cms', '-D', '-i', self.provision_path]
        process = Popen(decode_args, stdout=decoded_provision_fh)
        # if we don't wait for this to complete, it's likely
        # the next part will see a zero-length file
        process.wait()

        get_entitlements_cmd = [
            PLIST_BUDDY_BIN,
            '-x',
            '-c',
            'print :Entitlements ',
            decoded_provision_path]
        entitlements_fh = open(self.entitlements_path, 'w')
        process2 = Popen(get_entitlements_cmd, stdout=entitlements_fh)
        process2.wait()
        entitlements_fh.close()

        # should destroy the file
        decoded_provision_fh.close()

    def codesign(self, certificate, path, extra_args=[]):
        call([CODESIGN_BIN, '-f', '-s', certificate] + extra_args + [path])

    def sign(self, certificate):
        # first sign all the dylibs
        frameworks_path = os.path.join(self.app_dir, 'Frameworks')
        if os.path.exists(frameworks_path):
            dylibs = glob.glob(os.path.join(frameworks_path, '*.dylib'))
            for dylib in dylibs:
                self.codesign(certificate, dylib)
        # then sign the app
        self.codesign(certificate,
                      self.app_dir,
                      ['--entitlements', self.entitlements_path])

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


def absolute_path_argument(path):
    return os.path.abspath(path)


def exists_absolute_path_argument(path):
    if not os.path.exists(path):
        raise argparse.ArgumentTypeError("%s does not exist!" % path)
    return absolute_path_argument(path)


def app_argument(path):
    path = exists_absolute_path_argument(path)
    _, extension = os.path.splitext(path)
    if extension == '.app':
        app = ReceivedApp(path)
    elif extension == '.ipa':
        app = ReceivedIpaApp(path)
    else:
        raise argparse.ArgumentTypeError(
                "{0} doesn't seem to be an .app or .ipa".format(path))
    return app


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
            '-c', '--certificate',
            dest='certificate',
            required=True,
            metavar='<certificate>',
            help='Identifier for the certificate in your keychain. '
                 'See `security find-identity` for a list, or '
                 '`man codesign` for valid ways to specify it.')
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


if __name__ == '__main__':
    args = parse_args()
    received_app = args.app[0]

    if os.path.exists(args.stage_dir):
        shutil.rmtree(args.stage_dir)
    os.mkdir(args.stage_dir)

    app = received_app.unpack_to_dir(args.stage_dir)

    app.provision(args.provisioning_profile)

    app.create_entitlements()

    app.sign(args.certificate)

    output_path = app.package(args.output_path)

    if os.path.exists(args.stage_dir):
        shutil.rmtree(args.stage_dir)

    print "Re-signed package: {0}".format(output_path)
