""" Represents an app archive. This is an app at rest, whether it's a naked
    app bundle in a directory, or a zipped app bundle, or an IPA. We have a
    common interface to extract these apps to a temp file, then resign them,
    and create an archive of the same type """

import biplist
from bundle import App, Bundle, is_info_plist_native
from exceptions import NotSignable, NotMatched
from distutils import spawn
import logging
import os
from os.path import abspath, dirname, exists, isdir, join
import tempfile
import re
from subprocess import call
from signer import Signer
import shutil
import zipfile


REMOVE_WATCHKIT = True
helper_paths = {}
log = logging.getLogger(__name__)


def get_helper(helper_name):
    """ find paths to executables. Cached in helper_paths """
    if helper_name not in helper_paths or helper_paths[helper_name] is None:
        # note, find_executable returns None is not found
        # in other words, we keep retrying until found
        helper_paths[helper_name] = spawn.find_executable(helper_name)
    log.debug("got executable {} for {}".format(helper_paths[helper_name],
                                                helper_name))
    return helper_paths[helper_name]


def make_temp_dir():
    return tempfile.mkdtemp(prefix="isign-")


class AppArchive(object):
    """ The simplest form of archive -- a naked App Bundle, with no extra directory structure,
        compression, etc """
    def __init__(self, path):
        self.path = path

    def unarchive_to_temp(self):
        containing_dir = make_temp_dir()
        log.debug("unarchiving to temp... %s -> %s", self.path, containing_dir)
        shutil.rmtree(containing_dir)  # quirk of copytree, top dir can't exist already
        shutil.copytree(self.path, containing_dir)
        return containing_dir, App(containing_dir)

    @classmethod
    def archive(cls, path, output_path):
        if exists(output_path):
            shutil.rmtree(output_path)
        shutil.move(path, output_path)
        log.info("archived %s to %s" % (cls.__name__, output_path))


class AppZip(object):
    """ Just like an app, except it's zipped up, and when repackaged,
        should be re-zipped. """
    app_dir_pattern = r'^([^/]+\.app/).*$'
    extensions = ['.zip']
    helpers = ['zip', 'unzip']

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
            within the zipfile, b/c we don't want to make temp dirs just yet. This
            recapitulates a very similar precheck in the Bundle class """
        relative_app_dir = None
        is_native = False
        if (self.is_archive_extension_match() and
                zipfile.is_zipfile(self.path)):
            log.debug("this is an archive, and a zipfile")
            z = zipfile.ZipFile(self.path)
            apps = set()
            file_list = z.namelist()
            for file_name in file_list:
                matched = re.match(self.app_dir_pattern, file_name)
                if matched:
                    apps.add(matched.group(1))
            if len(apps) == 1:
                log.debug("found one app")
                relative_app_dir = apps.pop()
                plist_path = join(relative_app_dir, "Info.plist")
                plist_bytes = z.read(plist_path)
                plist = biplist.readPlistFromString(plist_bytes)
                is_native = is_info_plist_native(plist)
                log.debug("is_native: {}".format(is_native))
            if len(apps) > 1:
                log.warning('more than one app found in archive')

        return (relative_app_dir, is_native)

    def unarchive_to_temp(self):
        containing_dir = make_temp_dir()
        call([get_helper('unzip'), "-qu", self.path, "-d", containing_dir])
        app_dir = abspath(os.path.join(containing_dir, self.relative_app_dir))
        return containing_dir, App(app_dir)

    @classmethod
    def archive(cls, containing_dir, output_path):
        """ archive this up into a zipfile. Note this is a classmethod, because
            the caller will use us on a temp directory somewhere """
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
    app_dir_pattern = r'^(Payload/[^/]+\.app/).*$'


def archive_factory(path):
    """ Guess what kind of archive we are dealing with, return an
        archive object. """
    if isdir(path):
        try:
            return AppArchive(path)
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


def get_watchkit_paths(root_bundle_path):
    """ collect sub-bundles of this bundle that have watchkit """
    # typical structure:
    #
    # app_bundle
    #   ...
    #   some_directory
    #     watchkit_extension   <-- this is the watchkit bundle
    #       Info.plist
    #       watchkit_bundle    <-- this is the part that runs on the Watch
    #         Info.plist       <-- WKWatchKitApp=True
    #
    watchkit_paths = []
    for path, _, _ in os.walk(root_bundle_path):
        if path == root_bundle_path:
            continue
        try:
            bundle = Bundle(path)
        except NotMatched:
            # this directory is not a bundle
            continue
        if bundle.info.get('WKWatchKitApp') is True:
            # get the *containing* bundle
            watchkit_paths.append(dirname(path))
    return watchkit_paths


def process_watchkit(root_bundle_path, should_remove=False):
    """ Unfortunately, we currently can't sign WatchKit. If you don't
        care about watchkit functionality, it is
        generally harmless to remove it, so that's the default.
        Remove when https://github.com/saucelabs/isign/issues/20 is fixed """
    watchkit_paths = get_watchkit_paths(root_bundle_path)
    if len(watchkit_paths) > 0:
        if should_remove:
            for path in watchkit_paths:
                log.warning("Removing WatchKit bundle {}".format(path))
                shutil.rmtree(path)
        else:
            raise NotSignable("Cannot yet sign WatchKit bundles")

def view(input_path):
    if not exists(input_path):
        raise IOError("{0} not found".format(input_path))
    temp_dir = None
    bundle_info = None
    try:
        archive = archive_factory(input_path)
        (temp_dir, bundle) = archive.unarchive_to_temp()
        bundle_info = bundle.info
    except NotSignable as e:
        log.info("Could not read: <{0}>: {1}\n".format(input_path, e))
        raise
    finally:
        if temp_dir is not None and isdir(temp_dir):
            shutil.rmtree(temp_dir)
    return bundle_info

def resign(input_path,
           certificate,
           key,
           apple_cert,
           provisioning_profile,
           output_path,
           info_props=None):
    """ Unified interface to extract any kind of archive from
        a temporary file, resign it with these credentials,
        and create a similar archive for that resigned app """

    if not exists(input_path):
        raise IOError("{0} not found".format(input_path))

    signer = Signer(signer_cert_file=certificate,
                    signer_key_file=key,
                    apple_cert_file=apple_cert)

    temp_dir = None
    bundle_info = None
    try:
        archive = archive_factory(input_path)
        (temp_dir, bundle) = archive.unarchive_to_temp()
        if info_props:
            # Override info.plist props of the parent bundle
            bundle.update_info_props(info_props)
        process_watchkit(bundle.path, REMOVE_WATCHKIT)
        bundle.resign(signer, provisioning_profile)
        bundle_info = bundle.info
        archive.__class__.archive(temp_dir, output_path)
    except NotSignable as e:
        msg = "Not signable: <{0}>: {1}\n".format(input_path, e)
        log.info(msg)
        raise
    finally:
        if temp_dir is not None and isdir(temp_dir):
            shutil.rmtree(temp_dir)
    return bundle_info
