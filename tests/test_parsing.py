from isign_base_test import IsignBaseTest
import isign.bundle
from isign.signable import Executable
import logging

log = logging.getLogger(__name__)


class TestParsing(IsignBaseTest):
    """ This tests whether code signatures are parsed, by comparing
        stringified parses."""
    # Tests the parse-before-resign functionality used in
    # bin/pprint_codesig, which isn't exposed nicely as such.
    # Also see generate_codesig_construct_txt.py, to generate
    # the string this tests for
    def test_app(self):
        with open(self.TEST_APP_CODESIG_STR, 'r') as f:
            expected_codesig_str = f.read().strip()
        bundle = isign.bundle.App(self.TEST_APP)
        executable = Executable(bundle, bundle.get_executable_path(), None)
        arch = executable.arches[0]
        codesig_str = str(arch['cmds']['LC_CODE_SIGNATURE'])
        self.assertEquals(expected_codesig_str, codesig_str)
