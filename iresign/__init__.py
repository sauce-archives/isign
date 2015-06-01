# encoding: utf-8
import os.path
import json

package_dir = os.path.dirname(os.path.realpath(__file__))
with open(os.path.join(package_dir, "version.json"), 'r') as f:
    version = json.load(f)

__version__ = version['version']
__commit__ = version['commit']
__build__ = version['build']
