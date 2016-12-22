from isign_base_test import IsignBaseTest
import os
from os.path import exists
from isign.multisign import multisign
import logging

log = logging.getLogger(__name__)


class TestMultisign(IsignBaseTest):

    def test_multisign(self):
        output_path1 = self.get_temp_file()
        output_path2 = self.get_temp_file()
        creds_dir_to_output_paths = {
            self.CREDENTIALS_DIR: output_path1,
            self.CREDENTIALS_DIR_2: output_path2
        }
        results = multisign(self.TEST_IPA, creds_dir_to_output_paths)
        log.debug("results: %s", results)
        for output_path in [output_path1, output_path2]:
            assert exists(output_path)
            assert os.path.getsize(output_path) > 0
            self.unlink(output_path)
