from common_isign_test import TEST_APP
# from common_isign_test import TEST_APPZIP
from common_isign_test import TEST_IPA
from common_isign_test import TEST_NONAPP_TXT
from common_isign_test import TEST_NONAPP_IPA
from common_isign_test import KEY
from common_isign_test import CERTIFICATE
from common_isign_test import PROVISIONING_PROFILE
import os
from os.path import exists
from isign import isign
import shutil
import unittest


class TestPublicInterface(unittest.TestCase):
    credentials = {
        "key": KEY,
        "certificate": CERTIFICATE,
        "provisioning_profile": PROVISIONING_PROFILE
    }

    def _remove(self, path):
        if exists(path):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.unlink(path)

    def _resign(self, filename, **args):
        """ resign with test credentials """
        args.update(self.credentials)
        return isign.resign(filename, **args)

    def _test_signable(self, filename):
        with isign.new_from_archive(filename) as app:
            output_path = os.tmpnam()
            resigned_path = self._resign(app, output_path=output_path)
            assert exists(resigned_path)
            self._remove(resigned_path)

    def _test_unsignable(self, filename):
        with self.assertRaises(isign.NotSignable):
            with isign.new_from_archive(filename) as app:
                output_path = os.tmpnam()
                self._resign(app, output_path=output_path)

    def test_app(self):
        self._test_signable(TEST_APP)

    def test_app_ipa(self):
        self._test_signable(TEST_IPA)

    def test_non_app_txt(self):
        self._test_unsignable(TEST_NONAPP_TXT)

    def test_non_app_ipa(self):
        self._test_unsignable(TEST_NONAPP_IPA)
