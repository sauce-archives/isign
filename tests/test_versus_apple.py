from distutils import spawn
from isign_base_test import IsignBaseTest
import logging
from nose.plugins.skip import SkipTest
import os
from os.path import join
import platform
import re
import shutil
import subprocess
import tempfile
import zipfile

CODESIGN_BIN = spawn.find_executable('codesign')

log = logging.getLogger(__name__)


class TestVersusApple(IsignBaseTest):
    def codesign_display(self, path):
        """ inspect a path with codesign """
        cmd = [CODESIGN_BIN, '-d', '-r-', '--verbose=20', path]
        # n.b. codesign may print things to STDERR, or STDOUT, depending
        # on exactly what you're extracting. I KNOW RIGHT?
        proc = subprocess.Popen(cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        out, _ = proc.communicate()
        if proc.returncode != 0:
            log.debug(out)
            log.debug(_)
        assert proc.returncode == 0, "Return code not 0"
        return self.codesign_display_parse(out)

    def codesign_display_parse(self, out):
        """
        Parse codesign output into a dict.

        The output format is XML-like, in that it's a tree of nodes of
        varying types (including key-val pairs). We are assuming that
        it never gets more than 1 level deep (so, "array line" is just
        a special case here)
        """

        # designated => identifier "com.lyft.ios.enterprise.dev" and anchor...
        text_line = re.compile('^(\w[\w\s.]+) => (.*)$')

        # CodeDirectory v=20200 size=79151 flags=0x0(none) hashes=3948+5 ...
        props_line = re.compile('^(\w[\w\s.]+)\s+((?:\w+=\S+\s*)+)$')

        # Signed Time=May 14, 2015, 7:12:25 PM
        # Info.plist=not bound
        single_prop_line = re.compile('(\w[\w\s.]+)=(.*)$')

        # this assumes we only have one level of sub-arrays
        #    -3=969d263f74a5755cd3b4bede3f9e90c9fb0b7bca
        array_line = re.compile('\s+(-?\d+)=(.*)$')

        # last node assigned - used for appending sub-arrays, if encountered
        last = None

        ret = {}

        for line in out.splitlines():
            key = None
            val = None
            text_match = text_line.match(line)
            props_match = props_line.match(line)
            sp_match = single_prop_line.match(line)
            array_match = array_line.match(line)
            if text_match:
                key = text_match.group(1)
                val = text_match.group(2)
            elif props_match:
                key = props_match.group(1)
                val = {}
                pairs = re.split('\s+', props_match.group(2))
                for pair in pairs:
                    pairmatch = re.match('(\w+)=(\S+)', pair)
                    pairkey = pairmatch.group(1)
                    pairval = pairmatch.group(2)
                    val[pairkey] = pairval
            elif sp_match:
                key = sp_match.group(1)
                val = sp_match.group(2)
            elif array_match:
                if '_' not in last:
                    last['_'] = {}
                akey = array_match.group(1)
                aval = array_match.group(2)
                last['_'][akey] = aval
            else:
                # probably an error of some kind. These
                # get appended into the output too. :(
                if self.ERROR_KEY not in ret:
                    ret[self.ERROR_KEY] = []
                ret[self.ERROR_KEY].append(line)
            if key is not None:
                if key not in ret:
                    ret[key] = []
                ret[key].append(val)
                last = val

        return ret

    def get_dict_with_key(self, x, key):
        """ check a list for a dict that has a key """
        # e.g. if x = [ { 'a': 1 }, { 'b': 2 }]
        #      and key = 'a'
        #      return 1
        for item in x:
            if key in item:
                return item[key]
        return None

    def get_hashes_from_codesign_output_info(self, info):
        try:
            return self.get_dict_with_key(info['Hash'], '_') or info['Page'][0]['_']
        except KeyError:
            return None

    def assert_common_signed_properties(self, info):
        # has an executable
        assert 'Executable' in info

        # has an identifier
        assert 'Identifier' in info

        # has a codedirectory, embedded
        assert 'CodeDirectory' in info
        codedirectory_info = info['CodeDirectory'][0]
        assert codedirectory_info['location'] == 'embedded'

        # has a set of hashes
        assert 'Hash' in info
        hashes = self.get_hashes_from_codesign_output_info(info)

        assert hashes is not None

        # seal hash
        assert 'CDHash' in info

        # signed
        assert 'Signature' in info

        assert 'Authority' in info
        # The following only works with a cert signed by apple
        #
        # if isinstance(info['Authority'], list):
        #    authorities = info['Authority']
        # else:
        #    authorities = [info['Authority']]
        # assert 'Apple Root CA' in authorities

        assert 'Info.plist' in info
        assert self.get_dict_with_key(info['Info.plist'], 'entries') is not None

        assert 'TeamIdentifier' in info
        # TODO get this from an arg
        assert info['TeamIdentifier'][0] == self.OU

        assert 'designated' in info
        assert 'anchor apple generic' in info['designated'][0]

        # should have no errors
        assert self.ERROR_KEY not in info

    def assert_common_signed_hashes(self, info, start_index, end_index):
        assert 'Hash' in info
        hashes = self.get_hashes_from_codesign_output_info(info)
        assert hashes is not None
        for i in range(start_index, end_index + 1):
            assert str(i) in hashes
        return hashes

    def assert_hashes_for_signable(self, info, hashes_to_check):
        """ check that various hashes look right. """
        # Most of the hashes in the Hash section are hashes of blocks of the
        # object code in question. These all have positive subscripts.
        # But the "special" slots use negative numbers, and
        # are hashes of:
        # -5 Embedded entitlement configuration slot
        # -4 App-specific slot (in all the examples we know of, all zeroes)
        # -3 Resource Directory slot
        # -2 Requirements slot
        # -1 Info.plist slot
        # For more info, see codedirectory.h in Apple open source, e.g.
        # http://opensource.apple.com/source/libsecurity_codesigning/
        #   libsecurity_codesigning-55032/lib/codedirectory.h
        assert 'Hash' in info
        hashes = self.get_hashes_from_codesign_output_info(info)
        assert hashes is not None
        for i in hashes_to_check:
            key = str(i)
            assert key in hashes
            assert int(hashes[key], 16) != 0

    def assert_matching_identifier(self, app_path, expected):
        info = self.codesign_display(app_path)
        identifier = info['Identifier'][0]
        assert identifier == expected

    def check_bundle(self, path):
        """ look at info for bundles (apps and frameworks) """
        info = self.codesign_display(path)
        self.assert_common_signed_properties(info)
        assert 'Sealed Resources' in info
        self.assert_hashes_for_signable(info, [-5, -3, -2, -1])
        # TODO subject.CN from cert?

    def check_dylib(self, path):
        info = self.codesign_display(path)
        self.assert_common_signed_properties(info)
        self.assert_hashes_for_signable(info, [-2, -1])

    def test_override_identifier(self):
        """ Resign an app with identifiers of varying lengths, test that
            they were signed correctly with the new identifier  """
        # skip if this isn't a Mac with codesign installed
        if platform.system() != 'Darwin' or CODESIGN_BIN is None:
            raise SkipTest

#        old_cwd = os.getcwd()

        info = self.codesign_display(self.TEST_APP)
        original_id = info['Identifier'][0]

        # Make sure our original ID is long enough to test shorter bundle ids
        assert len(original_id) >= 6

        alphabet = 'abcdefghijklmnopqrstuvwxyz'
        while len(alphabet) <= len(original_id):
            alphabet += alphabet

        # Test with a shorter bundle ID
        short_id = alphabet[0:len(original_id) / 2 + 1]
        working_dir = tempfile.mkdtemp()
        os.chdir(working_dir)
        resigned_app_path = join(working_dir, 'Short.app')
        self.resign(self.TEST_APP,
                    output_path=resigned_app_path,
                    info_props={
                        'CFBundleIdentifier': short_id
                    })
        self.assert_matching_identifier(resigned_app_path, short_id)
        shutil.rmtree(working_dir)

        # Test with a longer bundle ID
        long_id = alphabet[0:len(original_id) + 1]
        working_dir = tempfile.mkdtemp()
        os.chdir(working_dir)
        resigned_app_path = join(working_dir, 'Long.app')
        self.resign(self.TEST_APP,
                    output_path=resigned_app_path,
                    info_props={
                        'CFBundleIdentifier': long_id
                    })
        self.assert_matching_identifier(resigned_app_path, long_id)

 #       os.chdir(old_cwd)
        shutil.rmtree(working_dir)


    def test_app(self):
        """ Extract a resigned app with frameworks, analyze if some expected
            things about them are true """
        # skip if this isn't a Mac with codesign installed
        if platform.system() != 'Darwin' or CODESIGN_BIN is None:
            raise SkipTest

        old_cwd = os.getcwd()

        # resign the test app that has frameworks, extract it to a temp directory
        working_dir = tempfile.mkdtemp()
        resigned_ipa_path = join(working_dir, 'resigned.ipa')
        self.resign(self.TEST_WITH_FRAMEWORKS_IPA,
                    output_path=resigned_ipa_path)
        os.chdir(working_dir)
        with zipfile.ZipFile(resigned_ipa_path) as zf:
            zf.extractall()

        # expected path to app
        # When we ask for codesign to analyze the app directory, it
        # will default to showing info for the main executable
        app_path = join(working_dir, 'Payload/isignTestApp.app')
        self.check_bundle(app_path)

        # Now we do similar tests for a dynamic library, linked to the
        # main executable.
        dylib_path = join(app_path, 'Frameworks', 'libswiftCore.dylib')
        self.check_dylib(dylib_path)

        # Now we do similar tests for a framework
        framework_path = join(app_path, 'Frameworks', 'FontAwesome_swift.framework')
        self.check_bundle(framework_path)

        os.chdir(old_cwd)
        shutil.rmtree(working_dir)


    def test_app_from_scratch(self):
        """ Test signing app bundles from scratch """
        # skip if this isn't a Mac with codesign installed
        if platform.system() != 'Darwin' or CODESIGN_BIN is None:
            raise SkipTest

        working_dir = tempfile.mkdtemp()
        signed_app_path = join(working_dir, 'signed.app')
        self.resign(self.TEST_UNSIGNED_THIN_APP,
                    output_path=signed_app_path)
        os.chdir(working_dir)

        # expected path to app
        # When we ask for codesign to analyze the app directory, it
        # will default to showing info for the main executable
        app_path = signed_app_path
        self.check_bundle(app_path)

        # Now we do similar tests for a dynamic library, linked to the
        # main executable.
        dylib_path = join(app_path, 'Frameworks', 'libswiftCore.dylib')
        self.check_dylib(dylib_path)


        shutil.rmtree(working_dir)


        working_dir = tempfile.mkdtemp()
        signed_app_path = join(working_dir, 'signed.app')
        self.resign(self.TEST_UNSIGNED_FAT_APP,
                    output_path=signed_app_path)
        os.chdir(working_dir)

        # expected path to app
        # When we ask for codesign to analyze the app directory, it
        # will default to showing info for the main executable
        app_path = signed_app_path
        self.check_bundle(app_path)

        # Now we do similar tests for a dynamic library, linked to the
        # main executable.
        dylib_path = join(app_path, 'Frameworks', 'libswiftCore.dylib')
        self.check_dylib(dylib_path)


        shutil.rmtree(working_dir)
