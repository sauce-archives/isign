# encoding: utf-8
from setuptools import setup, find_packages
from codecs import open  # to use a consistent encoding
from subprocess import check_output
from os import path, environ

here = path.abspath(path.dirname(__file__))

if path.exists(path.join(here, "version.sh")):  # development
    if 'PYTHON_PACKAGE_VERSION' in environ:
        version = environ['PYTHON_PACKAGE_VERSION']
    else:
        version = check_output(path.join(here, "version.sh")).strip()
    package_name = path.basename(here)
else:  # source package
    with open(path.join(here, "PKG-INFO")) as f:
        for line in f.readlines():
            if line.startswith("Version:"):
                version = line.split(":")[1].strip()
            elif line.startswith("Name:"):
                package_name = line.split(":")[1].strip()
package = package_name.replace('-', '_')

setup(
    name=package_name,
    version=version,
    description='Re-signing iOS apps without Apple tools',
    url='https://github.com/saucelabs/{}'.format(package_name),
    download_url='https://github.com/saucelabs/{}/tarball/v{}'.format(package_name, version),
    author='Sauce Labs',
    author_email='dev@saucelabs.com',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Utilities',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 2.7',
    ],
    keywords=['ios', 'app', 'signature', 'codesign', 'sign', 'resign'],
    packages=find_packages(),
    install_requires=[
        'biplist==0.9',
        'construct==2.5.2',
        'memoizer==0.0.1',
        'pyOpenSSL==0.15.1'
    ],
    package_data={
        package: ['apple_credentials/applecerts.pem',
                  'code_resources_template.xml',
                  'version.json'],
    },
    scripts=['bin/isign',
             'bin/isign_export_creds.sh',
             'bin/isign_guess_mobileprovision.sh']
)
