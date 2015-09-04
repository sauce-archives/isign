import biplist
import code_resources
import distutils
import glob
import logging
import os
from os.path import abspath, basename, exists, isdir, join, splitext
import re
from signer import Signer
import signable
import shutil
from subprocess import call
import tempfile
import zipfile


helper_paths = {}
log = logging.getLogger(__name__)


def get_helper(helper_name):
    """ find paths to executables. Cached in helper_paths """
    if helper_name not in helper_paths or helper_paths[helper_name] is None:
        # note, find_executable returns None is not found
        # in other words, we keep retrying until found
        helper_paths[helper_name] = distutils.spawn.find_executable(helper_name)
    log.debug("got executable {} for {}".format(helper_paths[helper_name],
                                                helper_name))
    return helper_paths[helper_name]


class NotSignable(Exception):
    """ superclass for any reason why app shouldn't be
        signable """
    pass


class NotMatched(NotSignable):
    """ thrown if we can't find any app class for
        this file path """
    pass


def make_temp_dir():
    return tempfile.mkdtemp(prefix="isign-")


def is_plist_native(plist):
    return (
        'CFBundleSupportedPlatforms' in plist and
        'iPhoneOS' in plist['CFBundleSupportedPlatforms']
    )


class App():
    helpers = []

    def precheck(self):
        """ Checks if a path looks like this kind of app,
            return stuff we'll need to know about its structure """
        is_native = False
        plist_path = join(self.path, "Info.plist")
        if exists(plist_path):
            log.debug("got a plist path, {}".format(plist_path))
            plist = biplist.readPlist(plist_path)
            is_native = is_plist_native(plist)
            log.debug("is native: {}".format(is_native))
        return is_native

    def unarchive_to_temp(self):
        containing_dir = make_temp_dir()
        log.info("unarchiving to temp... %s -> %s", self.path, containing_dir)
        shutil.rmtree(containing_dir)  # quirk of copytree, top dir can't exist already
        shutil.copytree(self.path, containing_dir)
        return containing_dir, App(containing_dir)

    def __init__(self, path):
        self.path = path
        is_native = self.precheck()
        if not is_native:
            raise NotMatched("not a native iOS app")

        self.entitlements_path = join(self.path,
                                      'Entitlements.plist')
        self.provision_path = join(self.path,
                                   'embedded.mobileprovision')

        # will be added later
        self.seal_path = None

        info_path = join(self.path, 'Info.plist')
        self.info = biplist.readPlist(info_path)

    def get_executable_path(self):
        executable_name = None
        if 'CFBundleExecutable' in self.info:
            executable_name = self.info['CFBundleExecutable']
        else:
            executable_name, _ = splitext(basename(self.path))
        executable = join(self.path, executable_name)
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
        frameworks_path = join(self.path, 'Frameworks')
        if exists(frameworks_path):
            dylib_paths = glob.glob(join(frameworks_path, '*.dylib'))
            for dylib_path in dylib_paths:
                dylib = signable.Dylib(dylib_path)
                dylib.sign(self, signer)
        # then create the seal
        # TODO maybe the app should know what its seal path should be...
        self.seal_path = code_resources.make_seal(self.get_executable_path(),
                                                  self.path)
        # then sign the app
        executable = signable.Executable(self.get_executable_path())
        executable.sign(self, signer)

    @classmethod
    def archive(cls, path, output_path):
        if exists(output_path):
            shutil.rmtree(output_path)
        shutil.move(path, output_path)
        log.info("archived %s to %s" % (cls.__name__, output_path))

    def resign(self, signer, provisioning_profile):
        """ signs app, modifies appdir in place """
        self.provision(provisioning_profile)
        self.create_entitlements(signer.team_id)
        self.sign(signer)
        log.info("Resigned app dir at <%s>", self.path)


class AppZip(object):
    """ Just like an app, except it's zipped up, and when repackaged,
        should be re-zipped. """
    app_dir_pattern = r'^[^/]+\.app/$'
    extensions = ['.zip']
    helpers = ['zip', 'unzip']

    def is_helpers_present(self):
        """ returns False if any of our helper apps wasn't found in class init """
        is_present = True
        for helper_name in self.helpers:
            if get_helper(helper_name) is None:
                log.error("missing helper for class {}: {}".format(self.__class__.__name__, helper_name))
                is_present = False
                break
        return is_present

    def is_archive_extension_match(self):
        """ does this path have the right extension """
        for extension in self.extensions:
            if self.path.endswith(extension):
                return True
        return False

    def precheck(self):
        """ Checks if an archive looks like this kind of app. Have to examine
            within the zipfile, b/c we don't want to make temp dirs just yet """
        relative_app_dir = None
        is_native = False
        if (self.is_archive_extension_match() and
                zipfile.is_zipfile(self.path)):
            log.debug("this is an archive, and a zipfile")
            z = zipfile.ZipFile(self.path)
            apps = []
            file_list = z.namelist()
            for file_name in file_list:
                if re.match(self.app_dir_pattern, file_name):
                    apps.append(file_name)
            if len(apps) == 1:
                log.debug("found one app")
                relative_app_dir = apps[0]
                plist_path = join(relative_app_dir, "Info.plist")
                plist_bytes = z.read(plist_path)
                plist = biplist.readPlistFromString(plist_bytes)
                is_native = is_plist_native(plist)
                log.debug("is_native: {}".format(is_native))
        return (relative_app_dir, is_native)

    def __init__(self, path):
        self.path = path
        if not self.is_helpers_present():
            raise NotSignable("helpers not present")
        relative_app_dir, is_native = self.precheck()
        self.relative_app_dir = relative_app_dir
        if relative_app_dir is None:
            raise NotMatched("no app directory found")
        if not is_native:
            raise NotMatched("not a native iOS app")

    def unarchive_to_temp(self):
        containing_dir = make_temp_dir()
        call([get_helper('unzip'), "-qu", self.path, "-d", containing_dir])
        app_dir = abspath(os.path.join(containing_dir, self.relative_app_dir))
        return containing_dir, App(app_dir)

    @classmethod
    def archive(cls, containing_dir, output_path):
        # the temp file is necessary because zip always adds ".zip" if it
        # does not have an extension. But we want to respect the desired
        # output_path's extension, which could be ".ipa" or who knows.
        # So we move it to the output_path later.
        #
        # We also do a little dance with making another temp directory just
        # to construct the zip file. This is the best way to ensure the an unused
        # filename. Also, `zip` won't overwrite existing files, so this is safer.
        temp_zip_dir = None
        old_cwd = None
        try:
            # need to chdir and use relative paths, because zip is stupid
            old_cwd = os.getcwd()
            os.chdir(containing_dir)
            temp_zip_dir = tempfile.mkdtemp(prefix="isign-zip-")
            temp_zip_file = join(temp_zip_dir, 'temp.zip')
            call([get_helper('zip'), "-qr", temp_zip_file, "."])
            shutil.move(temp_zip_file, output_path)
            log.info("archived %s to %s" % (cls.__name__, output_path))
        finally:
            if temp_zip_dir is not None and isdir(temp_zip_dir):
                shutil.rmtree(temp_zip_dir)
            if old_cwd is not None and isdir(old_cwd):
                os.chdir(old_cwd)


class Ipa(AppZip):
    """ IPA is Apple's standard for distributing apps. Much like an AppZip,
        but slightly different paths """
    extensions = ['.ipa']
    app_dir_pattern = r'^Payload/[^/]+\.app/$'


def app_archive_factory(path):
    """ factory to unpack various app types. """
    if isdir(path):
        try:
            return App(path)
        except NotSignable as e:
            log.error("Error initializing app dir: %s", e)
            raise NotSignable(e)
    else:
        obj = None
        for cls in [AppZip, Ipa]:
            try:
                obj = cls(path)
                log.debug("File %s matched as %s", path, cls.__name__)
                break
            except NotMatched as e:
                log.debug("File %s not matched as %s: %s", path, cls, e)
        if obj is not None:
            return obj

    raise NotSignable("No matching app format found for %s" % path)


def resign(input_path,
           certificate,
           key,
           apple_cert,
           provisioning_profile,
           output_path):
    signer = Signer(signer_cert_file=certificate,
                    signer_key_file=key,
                    apple_cert_file=apple_cert)

    temp_dir = None
    try:
        appArchive = app_archive_factory(input_path)
        (temp_dir, app) = appArchive.unarchive_to_temp()
        app.resign(signer, provisioning_profile)
        appArchive.__class__.archive(temp_dir, output_path)
    except NotSignable as e:
        msg = "Not signable: <{0}>: {1}\n".format(input_path, e)
        log.info(msg)
        raise
    finally:
        if temp_dir is not None and isdir(temp_dir):
            shutil.rmtree(temp_dir)
