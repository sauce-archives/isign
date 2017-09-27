'''
Some Py file
'''

from os import path

from setuptools import setup, find_packages

HERE = path.abspath(path.dirname(__file__))

__version__ = "0.10.2"
PACKAGE_NAME = "ak_isign"


setup(
    name=PACKAGE_NAME,
    version=__version__,
    description='Re-signing iOS apps without Apple tools',
    url='https://github.com/saucelabs/{}'.format(PACKAGE_NAME),
    download_url='https://github.com/saucelabs/{}/tarball/v{}'.format(
        PACKAGE_NAME, __version__),
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
        # 'biplist==0.9',
        'construct==2.8.14',
        'memoizer==0.0.1',
        'pyOpenSSL==17.2.0',
        'biplist==1.0.2'
    ],
    package_data={
        'isign': ['apple_credentials/applecerts.pem',
                  'code_resources_template.xml',
                  'version.json'],
    },
    scripts=['bin/isign',
             'bin/multisign',
             'bin/isign_export_creds.sh',
             'bin/isign_guess_mobileprovision.sh']
)
