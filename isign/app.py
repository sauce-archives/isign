import biplist
import code_resources
import distutils
import glob
import logging
import os
from os.path import abspath, basename, exists, join, splitext
import re
import signable
import shutil
from subprocess import call
import time
import tempfile
import zipfile

ZIP_BIN = distutils.spawn.find_executable('zip')
UNZIP_BIN = distutils.spawn.find_executable('unzip')
TAR_BIN = distutils.spawn.find_executable('tar')

log = logging.getLogger(__name__)


class NotSignable(Exception):
    """ superclass for any reason why app shouldn't be
        signable """
    pass


class NotMatched(NotSignable):
    """ thrown if we can't find any app class for
        this file path """
    pass


def get_unique_id():
    return str(int(time.time())) + '-' + str(os.getpid())


class App(object):
    extensions = ['.app']
    helpers = []

    @classmethod
    def is_helpers_present(cls):
        """ returns False if any of our helper apps wasn't found in class init """
        return reduce(lambda accum, h: accum and h is not None, cls.helpers, True)

    @classmethod
    def is_archive_extension_match(cls, path):
        """ does this path have the right extension """
        for extension in cls.extensions:
            if path.endswith(extension):
                return True
        return False

    @classmethod
    def is_plist_native(cls, plist):
        return (
            'CFBundleSupportedPlatforms' in plist and
            'iPhoneOS' in plist['CFBundleSupportedPlatforms']
        )

    @classmethod
    def make_temp_dir(cls):
        return tempfile.mkdtemp(prefix="isign-")

    @classmethod
    def precheck(cls, path):
        """ Checks if a path looks like this kind of app,
            return stuff we'll need to know about its structure """
        relative_app_dir = None
        is_native = False
        if cls.is_archive_extension_match(path):
            relative_app_dir = '.'
            plist_path = join(path, "Info.plist")
            if exists(plist_path):
                plist = biplist.readPlist(plist_path)
                is_native = cls.is_plist_native(plist)
        return (relative_app_dir, is_native)

    @classmethod
    def unarchive(cls, path, target_dir):
        log.debug("copying <%s> to <%s>", path, target_dir)
        shutil.rmtree(target_dir)  # quirk of copytree, top dir can't exist already
        shutil.copytree(path, target_dir)

    @classmethod
    def new_from_archive(cls, path):
        if not cls.is_helpers_present():
            log.error("Missing helpers for {}".format(cls.__name__))
            return False
        relative_app_dir, is_native = cls.precheck(path)
        if relative_app_dir is None or not is_native:
            return False
        target_dir = cls.make_temp_dir()
        cls.unarchive(path, target_dir)
        app_dir = abspath(os.path.join(target_dir, relative_app_dir))
        return cls(app_dir, target_dir)

    def __init__(self, path, containing_dir=None):
        self.path = path
        if containing_dir is None:
            containing_dir = self.path
        self.containing_dir = containing_dir
        self.entitlements_path = join(self.path,
                                      'Entitlements.plist')
        self.app_dir = self._get_app_dir()
        self.provision_path = join(self.app_dir,
                                   'embedded.mobileprovision')

        # will be added later
        self.seal_path = None

        try:
            info_path = join(self.app_dir, 'Info.plist')
            self.info = biplist.readPlist(info_path)
        except:
            self.cleanup()
            raise

    def __enter__(self):
        """ handle `with` initialization """
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        """ handle `with` destruction """
        log.debug('__exiting__ App class')
        self.cleanup()

    def cleanup(self):
        """ remove our temporary directories. Sometimes this
            has already been moved away """
        log.debug("cleaning up %s", self.containing_dir)
        if exists(self.containing_dir):
            shutil.rmtree(self.containing_dir)

    def _get_app_dir(self):
        return self.path

    def get_executable_path(self):
        executable_name = None
        if 'CFBundleExecutable' in self.info:
            executable_name = self.info['CFBundleExecutable']
        else:
            executable_name, _ = splitext(basename(self.app_dir))
        executable = join(self.app_dir, executable_name)
        if not exists(executable):
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
        log.debug("wrote Entitlements to {0}".format(self.entitlements_path))

    def sign(self, signer):
        # first sign all the dylibs
        frameworks_path = join(self.app_dir, 'Frameworks')
        if exists(frameworks_path):
            dylib_paths = glob.glob(join(frameworks_path, '*.dylib'))
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
        if exists(output_path):
            shutil.rmtree(output_path)
        shutil.move(self.app_dir, output_path)


class AppZip(App):
    """ Just like an app, except it's zipped up, and when repackaged,
        should be re-zipped. """
    app_dir_pattern = r'^[^/]+\.app/$'
    extensions = ['.zip']
    helpers = [ZIP_BIN, UNZIP_BIN]

    @classmethod
    def precheck(cls, path):
        """ Checks if a path looks like this kind of app,
            return stuff we'll need to know about its structure """
        log.info("precheck: %s %s", cls, path)
        relative_app_dir = None
        is_native = False
        if (cls.is_archive_extension_match(path) and zipfile.is_zipfile(path)):
            log.info("is an extension match, and is zipfile")
            z = zipfile.ZipFile(path)
            apps = []
            file_list = z.namelist()
            log.info("looking for app dir")
            for file_name in file_list:
                log.info("looking for app dir: %s", file_name)
                if re.match(cls.app_dir_pattern, file_name):
                    log.info("found app dir: %s", file_name)
                    apps.append(file_name)
            log.info("found apps: %s", apps)
            if len(apps) == 1:
                relative_app_dir = apps[0]
                plist_path = join(relative_app_dir, "Info.plist")
                log.info("plist path: %s", plist_path)
                plist_bytes = z.read(plist_path)
                plist = biplist.readPlistFromString(plist_bytes)
                is_native = cls.is_plist_native(plist)
                log.info("is_native? %s", is_native)
        return (relative_app_dir, is_native)

    @classmethod
    def unarchive(cls, path, target_dir):
        call([UNZIP_BIN, "-qu", path, "-d", target_dir])

    def archive(self, path, source_dir):
        call([ZIP_BIN, "-qr", path, source_dir])

    def get_temp_archive_name(self):
        return "out-" + get_unique_id() + self.extensions[0]

    def package(self, output_path):
        # we assume the caller uses the right extension for the output path.
        # need to chdir and use relative paths, because zip is stupid
        old_cwd = os.getcwd()
        os.chdir(self.containing_dir)
        relative_app_path = basename(self.path)
        temp = self.get_temp_archive_name()
        self.archive(temp, relative_app_path)
        shutil.move(temp, output_path)
        os.chdir(old_cwd)


class Ipa(AppZip):
    """ IPA is Apple's standard for distributing apps. Very much like
        an .app.zip, except different paths inside """
    extensions = ['.ipa']
    app_dir_pattern = r'^Payload/[^/]+\.app/$'

    def package(self, output_path):
        # we assume the caller uses the right extension for the output path.
        # need to chdir and use relative paths, because zip is stupid
        old_cwd = os.getcwd()
        os.chdir(self.containing_dir)
        log.info("inside %s", self.path)
        temp = self.get_temp_archive_name()
        log.info("archiving %s, %s", temp, "./Payload")
        self.archive(temp, "./Payload")
        log.info("moving %s to %s", temp, output_path)
        shutil.move(temp, output_path)
        os.chdir(old_cwd)


# in order of popularity on Pantry (aka sauce-storage)
FORMAT_CLASSES = [AppZip, Ipa, App]


def new_from_archive(path):
    """ factory to unpack various app types """

    for cls in FORMAT_CLASSES:
        log.info("trying format_class %s", cls.__name__)
        obj = cls.new_from_archive(path)
        log.info("obj is %s", obj)
        if obj is not False:
            return obj

    log.info("failed to find a format_class!")
    return False
