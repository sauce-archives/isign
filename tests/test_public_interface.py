from common_isign_test import TEST_APP
# from common_isign_test import TEST_APPZIP
from common_isign_test import TEST_IPA
from common_isign_test import TEST_NONAPP_TXT
from common_isign_test import TEST_NONAPP_IPA
import os
from os.path import exists
from isign import isign
import shutil
import unittest


class TestPublicInterface(unittest.TestCase):
    def _test_signable(self, filename):
        with isign.new_from_archive(filename) as app:
            output_path = os.tmpnam()
            resigned_path = isign.resign(app, output_path=output_path)
            print("resigned path:" + resigned_path)
            assert not exists(resigned_path)
            shutil.rmtree(resigned_path)

    def _test_unsignable(self, filename):
        with self.assertRaises(isign.NotSignable):
            with isign.new_from_archive(filename) as app:
                output_path = os.tmpnam()
                isign.resign(app, output_path=output_path)

    def test_app(self):
        self._test_signable(TEST_APP)

    def test_app_ipa(self):
        self._test_signable(TEST_IPA)

    def test_non_app_txt(self):
        self._test_unsignable(TEST_NONAPP_TXT)

    def test_non_app_ipa(self):
        self._test_unsignable(TEST_NONAPP_IPA)
