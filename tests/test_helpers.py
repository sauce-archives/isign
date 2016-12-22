import isign.archive
from isign.archive import AppZipArchive
from isign.exceptions import MissingHelpers
from isign_base_test import IsignBaseTest
from distutils import spawn
import logging


log = logging.getLogger(__name__)


class MissingHelpersArchive(AppZipArchive):
    """ An App whose helpers are not present """
    helpers = ['a_file_that_should_never_be_present']


def dummy_find_executable(name):
    return '/dummy/path/to/name'


class TestHelpers(IsignBaseTest):
    def test_helpers_is_present(self):
        """ test that missing helpers raises exception """
        with self.assertRaises(MissingHelpers):
            MissingHelpersArchive.precheck(self.TEST_APPZIP)

    def test_helpers_become_present(self):
        """ test that we can install helpers without restart """
        with self.assertRaises(MissingHelpers):
            MissingHelpersArchive.precheck(self.TEST_APPZIP)
        spawn._original_find_executable = spawn.find_executable
        spawn.find_executable = dummy_find_executable
        MissingHelpersArchive.precheck(self.TEST_APPZIP)
        if hasattr(spawn, '_original_find_executable'):
            spawn.find_executable = spawn._original_find_executable
        isign.archive.helper_paths = {}
