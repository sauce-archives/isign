from isign_base_test import IsignBaseTest
from isign.archive import archive_factory, Archive, AppArchive, AppZipArchive, IpaArchive
import logging

log = logging.getLogger(__name__)


class TestArchive(IsignBaseTest):

    def _test_good(self, filename, klass):
        archive = archive_factory(filename)
        assert archive is not None
        assert archive.__class__ is klass
        assert isinstance(archive, Archive)

    def test_archive_factory_app(self):
        self._test_good(self.TEST_APP, AppArchive)

    def test_archive_factory_appzip(self):
        self._test_good(self.TEST_APPZIP, AppZipArchive)

    def test_archive_factory_ipa(self):
        self._test_good(self.TEST_IPA, IpaArchive)

    def test_archive_factory_nonapp_dir(self):
        archive = archive_factory(self.TEST_NONAPP_DIR)
        assert archive is None

    def test_archive_factory_nonapp_ipa(self):
        archive = archive_factory(self.TEST_NONAPP_IPA)
        assert archive is None

    def test_archive_factory_nonapp_txt(self):
        archive = archive_factory(self.TEST_NONAPP_TXT)
        assert archive is None

    def test_archive_factory_nonapp_simulator_app(self):
        archive = archive_factory(self.TEST_SIMULATOR_APP)
        assert archive is None

    def test_archive_info(self):
        archive = archive_factory(self.TEST_IPA)
        assert archive is not None
        assert archive.bundle_info is not None
        assert archive.bundle_info['CFBundleName'] == 'isignTestApp'
