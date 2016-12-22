from isign.exceptions import MissingCredentials
from isign_base_test import IsignBaseTest
from isign import isign
import os
from os.path import exists, join
import logging

log = logging.getLogger(__name__)


class TestCredentialsDir(IsignBaseTest):

    def test_creds_dir(self):
        # this directory contains credentials with the standard names
        # key.pem, certificate.pem, isign.mobileprovision
        output_path = self.get_temp_file()
        isign.resign_with_creds_dir(self.TEST_IPA,
                                    self.CREDENTIALS_DIR,
                                    output_path=output_path)
        assert exists(output_path)
        assert os.path.getsize(output_path) > 0
        self.unlink(output_path)

    def test_bad_creds_dir(self):
        # while this contains credentials, they don't have standard names
        credentials_dir = join(self.TEST_DIR, 'credentials')
        output_path = self.get_temp_file()
        with self.assertRaises(MissingCredentials):
            isign.resign_with_creds_dir(self.TEST_IPA, credentials_dir, output_path=output_path)
        self.unlink(output_path)
