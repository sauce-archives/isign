from os.path import abspath
from os.path import dirname
from os.path import join

TEST_DIR = dirname(__file__)
TEST_APP = join(TEST_DIR, 'SimpleSaucyApp.app')
TEST_APPZIP = TEST_APP + '.zip'
TEST_IPA = join(TEST_DIR, 'SimpleSaucyApp.ipa')
TEST_NONAPP_TXT = join(TEST_DIR, 'NotAnApp.txt')
TEST_NONAPP_IPA = join(TEST_DIR, 'NotAnApp.ipa')
TEST_SIMULATOR_APP = join(TEST_DIR, 'IosSimulatorApp.app.zip')
REPO_ROOT = dirname(dirname(abspath(__file__)))
ISIGN_BIN = join(REPO_ROOT, 'isign', 'isign.py')
KEY = join(TEST_DIR, 'credentials', 'test.key.pem')
CERTIFICATE = join(TEST_DIR, 'credentials', 'test.cert.pem')
PROVISIONING_PROFILE = join(TEST_DIR, 'credentials', 'test.mobileprovision')
ERROR_KEY = '_errors'
# Sauce Labs apple organizational unit
OU = 'JWKXD469L2'
