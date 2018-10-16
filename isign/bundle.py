""" Represents a bundle. In the words of the Apple docs, it's a convenient way to deliver
    software. Really it's a particular kind of directory structure, with one main executable,
    well-known places for various data files and libraries,
    and tracking hashes of all those files for signing purposes.

    For isign, we have two main kinds of bundles: the App, and the Framework (a reusable
    library packaged along with its data files.) An App may contain many Frameworks, but
    a Framework has to be re-signed independently.

    See the Apple Developer Documentation "About Bundles" """

import biplist
import code_resources
from exceptions import NotMatched
import copy
import glob
import logging
import os
from os.path import basename, exists, join, splitext
from signer import openssl_command
import signable
import shutil


log = logging.getLogger(__name__)


def is_info_plist_native(plist):
    """ If an bundle is for native iOS, it has these properties in the Info.plist """
    return (
        'CFBundleSupportedPlatforms' in plist and
        'iPhoneOS' in plist['CFBundleSupportedPlatforms']
    )


class Bundle(object):
    """ A bundle is a standard directory structure, a signable, installable set of files.
        Apps are Bundles, but so are some kinds of Frameworks (libraries) """
    helpers = []
    signable_class = None

    def __init__(self, path):
        self.path = path
        self.info_path = join(self.path, 'Info.plist')
        if not exists(self.info_path):
            raise NotMatched("no Info.plist found; probably not a bundle")
        self.info = biplist.readPlist(self.info_path)
        self.orig_info = None
        if not is_info_plist_native(self.info):
            raise NotMatched("not a native iOS bundle")
        # will be added later
        self.seal_path = None

    def get_executable_path(self):
        """ Path to the main executable. For an app, this is app itself. For
            a Framework, this is the main framework """
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

    def update_info_props(self, new_props):
        if self.orig_info is None:
            self.orig_info = copy.deepcopy(self.info)

        changed = False
        if ('CFBundleIdentifier' in new_props and
                'CFBundleURLTypes' in self.info and
                'CFBundleURLTypes' not in new_props):
            # The bundle identifier changed. Check CFBundleURLTypes for
            # CFBundleURLName values matching the old bundle
            # id if it's not being set explicitly
            old_bundle_id = self.info['CFBundleIdentifier']
            new_bundle_id = new_props['CFBundleIdentifier']
            for url_type in self.info['CFBundleURLTypes']:
                if 'CFBundleURLName' not in url_type:
                    continue
                if url_type['CFBundleURLName'] == old_bundle_id:
                    url_type['CFBundleURLName'] = new_bundle_id
                    changed = True

        for key, val in new_props.iteritems():
            is_new_key = key not in self.info
            if is_new_key or self.info[key] != val:
                if is_new_key:
                    log.warn("Adding new Info.plist key: {}".format(key))
                self.info[key] = val
                changed = True

        if changed:
            biplist.writePlist(self.info, self.info_path, binary=True)
        else:
            self.orig_info = None

    def info_props_changed(self):
        return self.orig_info is not None

    def info_prop_changed(self, key):
        if not self.orig_info:
            # No props have been changed
            return False
        if key in self.info and key in self.orig_info and self.info[key] == self.orig_info[key]:
            return False
        return True

    def get_info_prop(self, key):
        return self.info[key]

    def sign_dylibs(self, signer, path):
        """ Sign all the dylibs in this directory """
        for dylib_path in glob.glob(join(path, '*.dylib')):
            dylib = signable.Dylib(self, dylib_path)
            dylib.sign(self, signer)

    def sign(self, signer):
        """ Sign everything in this bundle, recursively with sub-bundles """
        # log.debug("SIGNING: %s" % self.path)
        frameworks_path = join(self.path, 'Frameworks')
        if exists(frameworks_path):
            # log.debug("SIGNING FRAMEWORKS: %s" % frameworks_path)
            # sign all the frameworks
            for framework_name in os.listdir(frameworks_path):
                framework_path = join(frameworks_path, framework_name)
                # log.debug("checking for framework: %s" % framework_path)
                try:
                    framework = Framework(framework_path)
                    # log.debug("resigning: %s" % framework_path)
                    framework.resign(signer)
                except NotMatched:
                    # log.debug("not a framework: %s" % framework_path)
                    continue
            # sign all the dylibs under Frameworks
            self.sign_dylibs(signer, frameworks_path)

        # sign any dylibs in the main directory (rare, but it happens)
        self.sign_dylibs(signer, self.path)

        plugins_path = join(self.path, 'PlugIns')
        if exists(plugins_path):
            # sign the appex executables
            appex_paths = glob.glob(join(plugins_path, '*.appex'))
            for appex_path in appex_paths:
                plist_path = join(appex_path, 'Info.plist')
                if not exists(plist_path):
                    continue
                plist = biplist.readPlist(plist_path)
                appex_exec_path = join(appex_path, plist['CFBundleExecutable'])
                appex = signable.Appex(self, appex_exec_path, signer)
                appex.sign(self, signer)

        # then create the seal
        # TODO maybe the app should know what its seal path should be...
        self.seal_path = code_resources.make_seal(self.get_executable_path(),
                                                  self.path)
        # then sign the app
        executable = self.signable_class(self, self.get_executable_path())
        executable.sign(self, signer)

    def resign(self, signer):
        """ signs bundle, modifies in place """
        self.sign(signer)
        log.debug("Resigned bundle at <%s>", self.path)


class Framework(Bundle):
    """ A bundle that comprises reusable code. Similar to an app in that it has
        its own resources and metadata. Not like an app because the main executable
        doesn't have Entitlements, or an Application hash, and it doesn't have its
        own provisioning profile. """

    # the executable in this bundle will be a Framework
    signable_class = signable.Framework

    def __init__(self, path):
        super(Framework, self).__init__(path)


class App(Bundle):
    """ The kind of bundle that is visible as an app to the user.
        Contains the provisioning profile, entitlements, etc.  """

    # the executable in this bundle will be an Executable (i.e. the main
    # executable of an app)
    signable_class = signable.Executable

    def __init__(self, path):
        super(App, self).__init__(path)
        self.entitlements_path = join(self.path,
                                      'Entitlements.plist')
        self.provision_path = join(self.path,
                                   'embedded.mobileprovision')

    def provision(self, provision_path):
        shutil.copyfile(provision_path, self.provision_path)

    @staticmethod
    def extract_entitlements(provision_path):
        """ Given a path to a provisioning profile, return the entitlements
            encoded therein """
        cmd = [
            'smime',
            '-inform', 'der',
            '-verify',    # verifies content, prints verification status to STDERR,
                          #  outputs content to STDOUT. In our case, will be an XML plist
            '-noverify',  # accept self-signed certs. Not the opposite of -verify!
            '-in', provision_path
        ]
        # this command always prints 'Verification successful' to stderr.
        (profile_text, err) = openssl_command(cmd, data=None, expect_err=True)
        if err and err.strip() != 'Verification successful':
            log.error('Received unexpected error from openssl: {}'.format(err))
        plist_dict = biplist.readPlistFromString(profile_text)
        if 'Entitlements' not in plist_dict:
            log.debug('failed to get entitlements in provisioning profile')
            raise Exception('could not find Entitlements in {}'.format(provision_path))
        return plist_dict['Entitlements']

    def write_entitlements(self, signer, provisioning_path):
        """ Given a path to a provisioning profile, write its entitlements to
            self.entitlements_path """
        entitlements = self.extract_entitlements(provisioning_path)
        biplist.writePlist(entitlements, self.entitlements_path, binary=False)
        log.debug("wrote Entitlements to {0}".format(self.entitlements_path))

    def resign(self, signer, provisioning_profile):
        """ signs app in place """
        # copy the provisioning profile in
        self.provision(provisioning_profile)

        # Add entitlements from the pprof into the app
        self.write_entitlements(signer, provisioning_profile)

        # actually resign this bundle now
        super(App, self).resign(signer)
