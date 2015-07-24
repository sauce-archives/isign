from common_isign_test import TEST_APP
# from common_isign_test import TEST_APPZIP
from common_isign_test import TEST_IPA
from common_isign_test import TEST_NONAPP_TXT
from common_isign_test import TEST_NONAPP_IPA
from common_isign_test import TEST_SIMULATOR_APP
from common_isign_test import KEY
from common_isign_test import CERTIFICATE
from common_isign_test import PROVISIONING_PROFILE
from monitor_temp_file import MonitorTempFile
import os
from os.path import exists
from isign import isign
import shutil
import unittest
import tempfile


class TestPublicInterface(unittest.TestCase):
    credentials = {
        "key": KEY,
        "certificate": CERTIFICATE,
        "provisioning_profile": PROVISIONING_PROFILE
    }

    def setUp(self):
        """ this helps us monitor if we're not cleaning up temp files """
        MonitorTempFile.start()

    def tearDown(self):
        """ remove monitor on tempfile creation """
        MonitorTempFile.stop()

    def _get_temp_file(self, prefix='isign-test-'):
        (fd, path) = tempfile.mkstemp(prefix=prefix)
        os.close(fd)
        return path

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

    def _test_signable(self, filename, output_path):
        with isign.new_from_archive(filename) as app:
            resigned_path = self._resign(app, output_path=output_path)
            assert exists(resigned_path)
            assert os.path.getsize(resigned_path) > 0
            self._remove(resigned_path)
        assert MonitorTempFile.has_no_temp_files()

    def _test_unsignable(self, filename, output_path):
        with self.assertRaises(isign.NotSignable):
            with isign.new_from_archive(filename) as app:
                self._resign(app, output_path=output_path)
        self._remove(output_path)
        assert MonitorTempFile.has_no_temp_files()

    def _test_failed_to_sign(self, filename, output_path):
        with self.assertRaises(Exception):
            with isign.new_from_archive(filename) as app:
                self._resign(app, output_path=output_path)
        self._remove(output_path)
        assert MonitorTempFile.has_no_temp_files()

    def test_app(self):
        self._test_signable(TEST_APP, tempfile.mkdtemp('isign-test-'))

    def test_app_ipa(self):
        self._test_signable(TEST_IPA, self._get_temp_file())

    def test_non_app_txt(self):
        self._test_unsignable(TEST_NONAPP_TXT, self._get_temp_file())

    def test_non_app_ipa(self):
        self._test_failed_to_sign(TEST_NONAPP_IPA, self._get_temp_file())

    def test_simulator_app(self):
        self._test_unsignable(TEST_SIMULATOR_APP, self._get_temp_file())
