# encoding: utf-8
import os
from codecs import open
from setuptools import setup, find_packages
from subprocess import check_output
import json

PACKAGE_NAME = 'isign'

here = os.path.abspath(os.path.dirname(__file__))

if os.path.exists(os.path.join(here, "version.sh")):
    version = check_output(os.path.join(here, "version.sh")).strip()
else:
    with open(os.path.join(here, PACKAGE_NAME, "version.json")) as f:
        version = json.load(f)['version']


setup(
    name=PACKAGE_NAME,
    version=version,
    description='Signing or re-signing iOS apps without Apple tools',
    url='https://github.com/saucelabs/' + PACKAGE_NAME,
    author='Sauce Labs',
    author_email='dev@saucelabs.com',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Utilities',
        'License :: Other/Proprietary License',
        'Programming Language :: Python :: 2.7',
    ],
    keywords=PACKAGE_NAME + ' ios codesign provision',
    packages=find_packages(),
    install_requires=[
        'biplist==0.9',
        'construct==2.5.2',
        'hexdump==3.2',
        'memoizer==0.0.1',
        'pyOpenSSL==0.13'
    ],
    test_suite="tests",
    tests_require=['nose', 'pytest'],
    package_data={
        PACKAGE_NAME: ['version.json'],
    },
)
