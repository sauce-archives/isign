import distutils
from nose.plugins.skip import SkipTest
import os
from os.path import abspath
from os.path import dirname
from os.path import exists
from os.path import join
import platform
import pprint
import re
import shutil
import subprocess

CODESIGN_BIN = distutils.spawn.find_executable('codesign')
TEST_APP = join(dirname(__file__), 'SimpleSaucyApp.app')
TEST_APPZIP = TEST_APP + '.zip'
TEST_APPTGZ = join(dirname(__file__), 'SimpleSaucyApp.tgz')
TEST_IPA = join(dirname(__file__), 'SimpleSaucyApp.ipa')
REPO_ROOT = dirname(dirname(abspath(__file__)))
IRESIGN_BIN = join(REPO_ROOT, 'iresign', 'iresign.py')
APPLE_CERTIFICATES = join(REPO_ROOT, 'apple_credentials', 'applecerts.pem')
TEST_CREDENTIALS_DIR = join(REPO_ROOT, 'tests', 'credentials')
CERTIFICATE = join(TEST_CREDENTIALS_DIR, 'test.cert.pem')
KEY = join(TEST_CREDENTIALS_DIR, 'test.key.pem')
PROVISIONING_PROFILE = join(TEST_CREDENTIALS_DIR,
                            'integrationtests.mobileprovision')
ERROR_KEY = '_errors'
# Sauce Labs apple organizational unit
OU = 'JWKXD469L2'


class TestIntegration:
    def codesign_display(self, path):
        """ inspect a path with codesign """
        cmd = [CODESIGN_BIN, '-d', '-r-', '--verbose=20', path]
        # n.b. codesign usually prints everything to stderr
        proc = subprocess.Popen(cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        out, _ = proc.communicate()
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
            print line
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
                if ERROR_KEY not in ret:
                    ret[ERROR_KEY] = []
                ret[ERROR_KEY].append(line)
            if key is not None:
                if key in ret:
                    if not isinstance(ret[key], list):
                        ret[key] = [ret[key]]
                    ret[key].append(val)
                else:
                    ret[key] = val
                last = ret[key]

        return ret

    def assert_common_signed_properties(self, info):
        # has an executable
        assert 'Executable' in info

        # has an identifier
        assert 'Identifier' in info

        # has a codedirectory, embedded
        assert 'CodeDirectory' in info
        assert 'location' in info['CodeDirectory']
        assert info['CodeDirectory']['location'] == 'embedded'

        # has a set of hashes
        assert 'Hash' in info
        assert '_' in info['Hash']

        # seal hash
        assert 'CDHash' in info

        # signed
        assert 'Signature' in info

        assert 'Authority' in info
        if isinstance(info['Authority'], list):
            authorities = info['Authority']
        else:
            authorities = [info['Authority']]
        assert 'Apple Root CA' in authorities

        assert 'Info.plist' in info
        assert 'entries' in info['Info.plist']

        assert 'TeamIdentifier' in info
        # TODO get this from an arg
        assert info['TeamIdentifier'] == OU

        assert 'designated' in info
        assert 'anchor apple generic' in info['designated']

        # should have no errors
        assert ERROR_KEY not in info

    def assert_common_signed_hashes(self, info, start_index, end_index):
        # has a set of hashes
        assert 'Hash' in info
        assert '_' in info['Hash']
        hashes = info['Hash']['_']
        for i in range(start_index, end_index+1):
            assert str(i) in hashes
        return hashes

    def call_iresign(self,
                     output_path,
                     input_path,
                     key=KEY,
                     certificate=CERTIFICATE,
                     provisioning_profile=PROVISIONING_PROFILE,
                     apple_certificates=APPLE_CERTIFICATES):
        cmd = [IRESIGN_BIN,
               '-k', key,
               '-c', certificate,
               '-p', provisioning_profile,
               '-a', apple_certificates,
               '-o', output_path,
               input_path]
        print ' '.join(cmd)
        proc = subprocess.Popen(cmd)
        proc.communicate()
        assert proc.returncode == 0, "Return code not 0"

    def test_simple_app(self, cleanup=True):
        if platform.system() != 'Darwin' or CODESIGN_BIN is None:
            raise SkipTest
        app_path = 'test-out.app'
        self.call_iresign(input_path=TEST_APP, output_path=app_path)

        # When we ask for codesign to analyze the app directory, it
        # will default to showing info for the main executable
        app_info = self.codesign_display(app_path)
        self.assert_common_signed_properties(app_info)
        assert 'Sealed Resources' in app_info
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
        app_hashes = self.assert_common_signed_hashes(app_info, -5, -1)
        assert int(app_hashes['-5'], 16) != 0
        # skip slot -4, in all the examples we've seen it's always zero
        assert int(app_hashes['-3'], 16) != 0
        assert int(app_hashes['-2'], 16) != 0
        assert int(app_hashes['-1'], 16) != 0

        # Now we do similar tests for a dynamic library, linked to the
        # main executable.
        lib_path = join(app_path, 'Frameworks', 'libswiftCore.dylib')
        lib_info = self.codesign_display(lib_path)
        self.assert_common_signed_properties(lib_info)
        # dylibs only have -2 and -1
        lib_hashes = self.assert_common_signed_hashes(lib_info, -2, -1)
        assert int(lib_hashes['-2'], 16) != 0
        assert int(lib_hashes['-1'], 16) != 0
        assert '-3' not in lib_hashes

        # TODO subject.CN from cert?
        if cleanup:
            shutil.rmtree(app_path)
        return app_info

    def test_simple_ipa(self, cleanup=True):
        app_path = 'test-out.ipa'
        self.call_iresign(input_path=TEST_IPA, output_path=app_path)
        assert exists(app_path)

        # TODO subject.CN from cert?
        if cleanup:
            os.remove(app_path)

    def test_simple_appzip(self, cleanup=True):
        app_path = 'test-out.app.zip'
        self.call_iresign(input_path=TEST_APPZIP, output_path=app_path)
        assert exists(app_path)

        # todo subject.cn from cert?
        if cleanup:
            os.remove(app_path)

    def test_simple_apptgz(self, cleanup=True):
        app_path = 'test-out.tgz'
        self.call_iresign(input_path=TEST_APPTGZ, output_path=app_path)
        assert exists(app_path)

        # todo subject.cn from cert?
        if cleanup:
            os.remove(app_path)

if __name__ == '__main__':
    x = TestIntegration()
    pp = pprint.PrettyPrinter(indent=2)
    pp.pprint(x.test_simple_app(False))
    pp.pprint(x.test_simple_ipa(False))
    pp.pprint(x.test_simple_appzip(False))
    pp.pprint(x.test_simple_apptgz(False))
