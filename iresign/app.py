import biplist
import code_resources
import glob
import os
import os.path
import signable
import shutil
from subprocess import call


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

    def create_entitlements(self, team_id):
        entitlements = {
            "keychain-access-groups": [team_id + '.*'],
            "com.apple.developer.team-identifier": team_id,
            "application-identifier": team_id + '.*',
            "get-task-allow": True
        }
        biplist.writePlist(entitlements, self.entitlements_path, binary=False)
        print "wrote Entitlements to {0}".format(self.entitlements_path)

    def sign(self, signer):
        # first sign all the dylibs
        frameworks_path = os.path.join(self.app_dir, 'Frameworks')
        if os.path.exists(frameworks_path):
            dylib_paths = glob.glob(os.path.join(frameworks_path, '*.dylib'))
            for dylib_path in dylib_paths:
                dylib = signable.Dylib(self, dylib_path)
                dylib.sign(signer)
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


