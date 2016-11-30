from isign_base_test import IsignBaseTest
from isign.bundle import App
import logging

log = logging.getLogger(__name__)


class TestEntitlements(IsignBaseTest):
    def test_entitlements_extraction(self):
        entitlements = App.extract_entitlements(self.PROVISIONING_PROFILE)
        log.debug(entitlements)
        assert entitlements['application-identifier'] == 'ISIGNTESTS.*'
        assert entitlements['get-task-allow'] == True
