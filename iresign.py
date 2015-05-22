#!/usr/bin/env python

import argparse
import biplist
from codesig import Codesig
import code_resources
import distutils
import glob
# import isign
from signer import Signer
import macho
import os
import os.path
import shutil
from subprocess import call
import tempfile

ZIP_BIN = distutils.spawn.find_executable('zip')
UNZIP_BIN = distutils.spawn.find_executable('unzip')

# Sauce Labs Apple Organizational Unit
TEAM_ID = 'JWKXD469L2'


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

        # will be added later
        self.seal_path = None

        info_path = os.path.join(self.get_app_dir(), 'Info.plist')
        if not os.path.exists(info_path):
            raise Exception('no Info.plist at {0}'.format(info_path))
        self.info = biplist.readPlist(info_path)

    def get_app_dir(self):
        return self.path

    def get_executable(self):
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

    def sign_arch(self, arch_macho, arch_end, f, signer):
        cmds = {}
        for cmd in arch_macho.commands:
            name = cmd.cmd
            cmds[name] = cmd

        if 'LC_CODE_SIGNATURE' in cmds:
            lc_cmd = cmds['LC_CODE_SIGNATURE']
            # re-sign
            print "re-signing"
            codesig_offset = arch_macho.macho_start + lc_cmd.data.dataoff
            f.seek(codesig_offset)
            codesig_data = f.read(lc_cmd.data.datasize)
            # print len(codesig_data)
            # print hexdump(codesig_data)
        else:
            raise Exception("not implemented")
            # TODO: this doesn't actually work :(
            # codesig_data = isign.make_signature(arch_macho, arch_end,
            #                                     cmds, f,
            #                                     self.entitlements_path)
            # TODO get the data from construct back

        codesig = Codesig(codesig_data)
        codesig.resign(self.entitlements_path, self.seal_path, signer, TEAM_ID)

        # print new_codesig_cons
        new_codesig_data = codesig.build_data()
        print "old len:", len(codesig_data)
        print "new len:", len(new_codesig_data)

        padding_length = len(codesig_data) - len(new_codesig_data)
        new_codesig_data += "\x00" * padding_length
        print "padded len:", len(new_codesig_data)
        print "----"
        # print hexdump(new_codesig_data)
        # assert new_codesig_data != codesig_data

        lc_cmd = cmds['LC_CODE_SIGNATURE']
        lc_cmd.data.datasize = len(new_codesig_data)
        lc_cmd.bytes = macho.CodeSigRef.build(cmd.data)

        offset = lc_cmd.data.dataoff
        return offset, new_codesig_data

    # TODO maybe split into different signing methods for
    # dylibs and executables? the sig is constructed slightly differently
    def sign_file(self, filename, signer):
        print "working on {0}".format(filename)

        f = open(filename, "rb")
        m = macho.MachoFile.parse_stream(f)
        arch_macho = m.data
        f.seek(0, os.SEEK_END)
        file_end = f.tell()
        arches = []
        if 'FatArch' in arch_macho:
            for i, arch in enumerate(arch_macho.FatArch):
                a = {'macho': arch.MachO}
                next_macho = i + 1
                if next_macho == len(arch_macho.FatArch):  # last
                    a['macho_end'] = file_end
                else:
                    next_arch = arch_macho.FatArch[next_macho]
                    a['macho_end'] = next_arch.MachO.macho_start
                arches.append(a)
        else:
            arches.append({'macho': arch_macho, 'macho_end': file_end})

        # copy f into temp, reset to beginning of file
        temp = tempfile.NamedTemporaryFile('wb', delete=False)
        f.seek(0)
        temp.write(f.read())
        temp.seek(0)

        # write new codesign blocks for each arch
        offset_fmt = ("offset: {2}, write offset: {0}, "
                      "new_codesig_data len: {1}")
        for arch in arches:
            offset, new_codesig_data = self.sign_arch(arch['macho'],
                                                      arch['macho_end'],
                                                      f,
                                                      signer)
            write_offset = arch['macho'].macho_start + offset
            print offset_fmt.format(write_offset,
                                    len(new_codesig_data),
                                    offset)
            temp.seek(write_offset)
            temp.write(new_codesig_data)

        # write new headers
        temp.seek(0)
        macho.MachoFile.build_stream(m, temp)
        temp.close()

        print "moving temporary file to {0}".format(filename)
        os.rename(temp.name, filename)

    def sign(self, signer):
        # first sign all the dylibs
        frameworks_path = os.path.join(self.app_dir, 'Frameworks')
        if os.path.exists(frameworks_path):
            dylibs = glob.glob(os.path.join(frameworks_path, '*.dylib'))
            for dylib in dylibs:
                self.sign_file(dylib, signer)
        # then create the seal
        self.seal_path = code_resources.make_seal(self.get_executable(),
                                                  self.get_app_dir())
        # then sign the app
        self.sign_file(self.get_executable(), signer)

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
    return os.path.abspath(os.path.expanduser(path))


def exists_absolute_path_argument(path):
    path = absolute_path_argument(path)
    if not os.path.exists(path):
        raise argparse.ArgumentTypeError("%s does not exist!" % path)
    return path


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


if __name__ == '__main__':
    args = parse_args()
    received_app = args.app[0]

    if os.path.exists(args.stage_dir):
        shutil.rmtree(args.stage_dir)
    os.mkdir(args.stage_dir)

    app = received_app.unpack_to_dir(args.stage_dir)

    app.provision(args.provisioning_profile)

    app.create_entitlements()

    signer = Signer(signer_cert_file=args.certificate,
                    signer_key_file=args.key,
                    apple_cert_file=args.apple_cert)

    app.sign(signer)

    output_path = app.package(args.output_path)

    if os.path.exists(args.stage_dir):
        shutil.rmtree(args.stage_dir)

    print "Re-signed package: {0}".format(output_path)
