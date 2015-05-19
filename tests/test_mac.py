import platform
import pytest


@pytest.mark.skipif(platform.system() != 'Darwin',
                    reason="need a Mac to run")
class TestMac:
    def test_true(self):
        assert True
