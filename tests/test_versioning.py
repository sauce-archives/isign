#!/usr/bin/env python
import os.path
import importlib
import unittest

tests_dir = os.path.abspath(os.path.dirname(__file__))
package_name = tests_dir.split(os.path.sep)[-2].replace('-', '_')
package = importlib.import_module(package_name)


class VersioningTestCase(unittest.TestCase):

    def assert_proper_attribute(self, attribute):
        try:
            assert getattr(package, attribute), (
                "{} improperly set".format(attribute))
        except AttributeError:
            assert False, "missing {}".format(attribute)

    def test_version_attribute(self):
        self.assert_proper_attribute("__version__")

        # test major, minor, and patch are numbers
        version_split = package.__version__.split(".")[:3]
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
