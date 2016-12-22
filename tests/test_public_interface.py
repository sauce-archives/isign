from isign_base_test import IsignBaseTest
import os
from os.path import exists
from isign import isign
import logging

log = logging.getLogger(__name__)


class TestPublicInterface(IsignBaseTest):

    def _test_signable(self, filename, output_path):
        self.resign(filename, output_path=output_path)
        assert exists(output_path)
        assert os.path.getsize(output_path) > 0
        self.unlink(output_path)

    def _test_unsignable(self, filename, output_path):
        with self.assertRaises(isign.NotSignable):
            self.resign(filename, output_path=output_path)
        self.unlink(output_path)

    def test_app(self):
        self._test_signable(self.TEST_APP, self.get_temp_dir())

    def test_app_ipa(self):
        self._test_signable(self.TEST_IPA, self.get_temp_file())

    def test_app_with_frameworks_ipa(self):
        self._test_signable(self.TEST_WITH_FRAMEWORKS_IPA, self.get_temp_file())

    def test_appzip(self):
        self._test_signable(self.TEST_APPZIP, self.get_temp_file())

    def test_non_app_txt(self):
        self._test_unsignable(self.TEST_NONAPP_TXT, self.get_temp_file())

    def test_non_app_ipa(self):
        self._test_unsignable(self.TEST_NONAPP_IPA, self.get_temp_file())

    def test_simulator_app(self):
        self._test_unsignable(self.TEST_SIMULATOR_APP, self.get_temp_file())
