#!/usr/bin/env python
import unittest

import isign


class VersioningTestCase(unittest.TestCase):

    def assert_proper_attribute(self, attribute):
        try:
            assert getattr(isign, attribute), (
                "{} improperly set".format(attribute))
        except AttributeError:
            assert False, "missing {}".format(attribute)

    def test_version_attribute(self):
        self.assert_proper_attribute("__version__")

        # test major, minor, and patch are numbers
        version_split = isign.__version__.split(".")[:3]
        assert version_split, "__version__ is not set"
        for n in version_split:
            try:
                int(n)
            except ValueError:
                assert False, "'{}' is not an integer".format(n)

    def test_commit_attribute(self):
        self.assert_proper_attribute("__commit__")

    def test_build_attribute(self):
        self.assert_proper_attribute("__build__")


if __name__ == '__main__':
    unittest.main()
