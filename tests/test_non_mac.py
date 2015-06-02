import hashlib
import os
from os.path import abspath
from os.path import dirname
from os.path import exists
from os.path import join
import platform
import pprint
import pytest
import subprocess

TEST_APP = join(dirname(__file__), 'SimpleSaucyApp.app')
TEST_IPA = join(dirname(__file__), 'SimpleSaucyApp.ipa')
IRESIGN_BIN = join(dirname(dirname(abspath(__file__))),
                   'iresign/iresign.py')
CREDS_DIR = os.environ['HOME']
APPLE_CERTIFICATES = join(CREDS_DIR, 'applecerts.pem')
CERTIFICATE = join(CREDS_DIR, 'mobdev.pem')
KEY = join(CREDS_DIR, 'mobdev.p12')
PROVISIONING_PROFILE = join(CREDS_DIR, 'mobdev1.mobileprovision')
# Sauce Labs apple organizational unit
HASH_BLOCKSIZE = 65536


def get_hash_hex_md5(path):
    """ Get the hash of a file at path, encoded as hexadecimal """
    hasher = hashlib.md5()
    with open(path, 'rb') as afile:
        buf = afile.read(HASH_BLOCKSIZE)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(HASH_BLOCKSIZE)
    return hasher.hexdigest()


@pytest.mark.skipif(platform.system() == 'Darwin',
                    reason="Redundant test if on Mac")
class TestLinux:

    def test_simple_ipa(self, cleanup=True):
        app_path = 'test-out-linux.ipa'
        cmd = [IRESIGN_BIN,
               '-p', PROVISIONING_PROFILE,
               '-k', KEY,
               '-c', CERTIFICATE,
               '-a', APPLE_CERTIFICATES,
               '-o', app_path,
               TEST_IPA]
        print ' '.join(cmd)
        proc = subprocess.Popen(cmd)
        proc.communicate()
        assert proc.returncode == 0, "Return code not 0"
        assert exists(app_path)

        # TODO subject.CN from cert?
        if cleanup:
            os.remove(app_path)


if __name__ == '__main__':
    x = TestLinux()
    pp = pprint.PrettyPrinter(indent=2)
    pp.pprint(x.test_simple_ipa(False))
