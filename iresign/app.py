import biplist
import code_resources
import distutils
import glob
import logging
import os
import os.path
import signable
import shutil
from subprocess import call, Popen
import time

ZIP_BIN = distutils.spawn.find_executable('zip')
UNZIP_BIN = distutils.spawn.find_executable('unzip')
FILE_BIN = distutils.spawn.find_executable('file')

log = logging.getLogger(__name__)


class App(object):
    extensions = ['.app']

    @classmethod
    def new_from_package(cls, path, target_dir):
        app_name = os.path.basename(path)
        app_dir = os.path.join(target_dir, app_name)
        shutil.copytree(path, app_dir)
        return cls(app_dir)

    def __init__(self, path):
        self.path = path
        self.entitlements_path = os.path.join(self.path,
                                              'Entitlements.plist')
        self.app_dir = self._get_app_dir()
        self.provision_path = os.path.join(self.app_dir,
                                           'embedded.mobileprovision')

        # will be added later
        self.seal_path = None

        info_path = os.path.join(self.app_dir, 'Info.plist')
        if not os.path.exists(info_path):
            raise Exception('no Info.plist at {0}'.format(info_path))
        self.info = biplist.readPlist(info_path)

    def _get_app_dir(self):
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

    def is_native(self):
        return (
            'CFBundleSupportedPlatforms' in self.info
            and
            'iPhoneOS' in self.info['CFBundleSupportedPlatforms']
        )

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
        log.debug("wrote Entitlements to {0}".format(self.entitlements_path))

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
                                                  self.app_dir)
        # then sign the app
        executable = signable.Executable(self, self.get_executable_path())
        executable.sign(signer)

    def package(self, output_path):
        os.rename(self.app_dir, output_path)


class AppZip(App):
    """ Just like an app, except it's zipped up, and when repackaged,
        should be re-zipped """
    extensions = ['.app.zip']

    @classmethod
    def find_app(cls, path):
        glob_path = os.path.join(path, '*.app')
        apps = glob.glob(glob_path)
        count = len(apps)
        if count != 1:
            err = "Expected 1 app in {0}, found {1}".format(glob_path, count)
            raise Exception(err)
        return apps[0]

    @classmethod
    def new_from_package(cls, path, target_dir):
        call([UNZIP_BIN, "-qu", path, "-d", target_dir])
        app_dir = cls.find_app(target_dir)
        return cls(app_dir)

    def _get_temp_zip_name(self):
        return "out-" + str(os.getpid()) + '-' + str(int(time.time())) + ".zip"

    def package(self, output_path):
        # we assume the caller uses the right extension for the output path.
        # need to chdir and use relative paths, because zip is stupid
        old_cwd = os.getcwd()
        os.chdir(os.path.dirname(self.path))
        relative_app_path = os.path.basename(self.path)
        temp = self._get_temp_zip_name()
        call([ZIP_BIN, "-qr", temp, relative_app_path])
        os.rename(temp, output_path)
        os.chdir(old_cwd)


class Ipa(AppZip):
    """ IPA is Apple's standard for distributing apps. Very much like
        an .app.zip, except different paths inside """
    extensions = ['.ipa']

    @classmethod
    def new_from_package(cls, path, target_dir):
        call([UNZIP_BIN, "-qu", path, "-d", target_dir])
        return cls(target_dir)

    def _get_payload_dir(self):
        return os.path.join(self.path, "Payload")

    def _get_app_dir(self):
        return self.find_app(self._get_payload_dir())

    def package(self, output_path):
        # we assume the caller uses the right extension for the output path.
        # need to chdir and use relative paths, because zip is stupid
        old_cwd = os.getcwd()
        os.chdir(self.path)
        relative_payload_path = os.path.relpath(
                self._get_payload_dir(),
                self.path)
        temp = self._get_temp_zip_name()
        call([ZIP_BIN, "-qr", temp, relative_payload_path])
        os.rename(temp, output_path)
        os.chdir(old_cwd)


APP_CLASSES = [Ipa, App, AppZip]


def new_from_package(path, target_dir):
    """ factory to unpack various app types """
    for cls in APP_CLASSES:
        for extension in cls.extensions:
            if path.endswith(extension):
                app = cls.new_from_package(path, target_dir)
                # TODO test for re-signability
                return app
    return False
