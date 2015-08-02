from common_isign_test import TEST_APP
# from common_isign_test import TEST_APPZIP
from common_isign_test import TEST_IPA
from common_isign_test import TEST_NONAPP_TXT
from common_isign_test import TEST_NONAPP_IPA
from common_isign_test import TEST_SIMULATOR_APP
from common_isign_test import KEY
from common_isign_test import CERTIFICATE
from common_isign_test import PROVISIONING_PROFILE
import logging
from monitor_temp_file import MonitorTempFile
import os
from os.path import exists
from isign import isign
import shutil
import unittest
import tempfile

log = logging.getLogger(__name__)


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

    def _resign_with_test_credentials(self, filename, **args):
        """ resign with test credentials """
        args.update(self.credentials)
        return isign.resign(filename, **args)

    def _check_no_temp_files_left(self):
        remaining_temp_files = MonitorTempFile.get_temp_files()
        if len(remaining_temp_files) != 0:
            log.error("remaining temp files: %s",
                      ', '.join(remaining_temp_files))
        assert len(remaining_temp_files) == 0

    def _test_signable(self, filename, output_path):
        self._resign_with_test_credentials(filename,
                                           output_path=output_path)
        assert exists(output_path)
        assert os.path.getsize(output_path) > 0
        self._remove(output_path)
        self._check_no_temp_files_left()

    def _test_unsignable(self, filename, output_path):
        with self.assertRaises(isign.app.NotSignable):
            self._resign_with_test_credentials(filename,
                                               output_path=output_path)
        self._remove(output_path)
        self._check_no_temp_files_left()

    def test_app(self):
        self._test_signable(TEST_APP, tempfile.mkdtemp('isign-test-'))

    def test_app_ipa(self):
        self._test_signable(TEST_IPA, self._get_temp_file())

    def test_non_app_txt(self):
        self._test_unsignable(TEST_NONAPP_TXT, self._get_temp_file())

    def test_non_app_ipa(self):
        self._test_unsignable(TEST_NONAPP_IPA, self._get_temp_file())

    def test_simulator_app(self):
        self._test_unsignable(TEST_SIMULATOR_APP, self._get_temp_file())
