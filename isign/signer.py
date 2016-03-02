#
# Small object that can be passed around easily, that represents
# our signing credentials, and can sign data.
#
# Unfortunately the installed python OpenSSL library doesn't
# offer what we need for cms, so we also need to shell out to the openssl
# tool, and make sure it's the right version.

from distutils import spawn
import logging
from OpenSSL import crypto
import os
import os.path
import subprocess
import re

OPENSSL = os.getenv('OPENSSL', spawn.find_executable('openssl'))
# modern OpenSSL versions look like '0.9.8zd'. Use a regex to parse
OPENSSL_VERSION_RE = re.compile(r'(\d+).(\d+).(\d+)(\w*)')
MINIMUM_OPENSSL_VERSION = '1.0.1'

log = logging.getLogger(__name__)


def openssl_command(args, data=None):
    """ given array of args, and optionally data to write,
        return results of openssl command """
    cmd = [OPENSSL] + args
    cmd_str = ' '.join(cmd)
    # log.debug('running command ' + cmd_str)
    proc = subprocess.Popen(cmd,
                            stdin=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            stdout=subprocess.PIPE)
    if data is not None:
        proc.stdin.write(data)
    out, err = proc.communicate()
    if err is not None and err != '':
        log.error("Command `{0}` returned error:\n{1}".format(cmd_str, err))
    if proc.returncode != 0:
        msg = "openssl command `{0}` failed, see log for error".format(cmd_str)
        raise Exception(msg)
    return out


def get_installed_openssl_version():
    version_line = openssl_command(['version'])
    # e.g. 'OpenSSL 0.9.8zd 8 Jan 2015'
    return re.split(r'\s+', version_line)[1]


def is_openssl_version_ok(version, minimum):
    """ check that the openssl tool is at least a certain version """
    version_tuple = openssl_version_to_tuple(version)
    minimum_tuple = openssl_version_to_tuple(minimum)
    return version_tuple >= minimum_tuple


def openssl_version_to_tuple(s):
    """ OpenSSL uses its own versioning scheme, so we convert to tuple,
        for easier comparison """
    search = re.search(OPENSSL_VERSION_RE, s)
    if search is not None:
        return search.groups()
    return ()


class Signer(object):
    """ collaborator, holds the keys, identifiers for signer,
        and knows how to sign data """
    def __init__(self,
                 signer_key_file=None,
                 signer_cert_file=None,
                 apple_cert_file=None,
                 team_id=None):
        """ signer_key_file = your org's key .pem
            signer_cert_file = your org's cert .pem
            apple_cert_file = apple certs in .pem form
            team_id = your Apple Organizational Unit code """
        for filename in [signer_key_file, signer_cert_file, apple_cert_file]:
            if not os.path.exists(filename):
                msg = "Can't find {0}".format(filename)
                log.warn(msg)
                raise Exception(msg)
        self.signer_key_file = signer_key_file
        self.signer_cert_file = signer_cert_file
        self.apple_cert_file = apple_cert_file
        team_id = self._get_team_id()
        if team_id is None:
            raise Exception("Cert file does not contain Subject line"
                            "with Apple Organizational Unit (OU)")
        self.team_id = team_id
        self.check_openssl_version()

    def check_openssl_version(self):
        openssl_version = get_installed_openssl_version()
        if not is_openssl_version_ok(openssl_version, MINIMUM_OPENSSL_VERSION):
            msg = "Signing may not work: OpenSSL version is {0}, need {1} !"
            log.warn(msg.format(openssl_version, MINIMUM_OPENSSL_VERSION))

    def sign(self, data):
        """ sign data, return filehandle """
        cmd = [
            "cms",
            "-sign", "-binary", "-nosmimecap",
            "-certfile", self.apple_cert_file,
            "-signer", self.signer_cert_file,
            "-inkey", self.signer_key_file,
            "-keyform", "pem",
            "-outform", "DER"
        ]
        signature = openssl_command(cmd, data)
        # in some cases we've seen this return a zero length file.
        # Misconfigured machines?
        if len(signature) < 128:
            too_small_msg = "Command `{0}` returned success, but signature "
            "seems too small ({1} bytes)"
            raise Exception(too_small_msg.format(' '.join(cmd),
                                                 len(signature)))
        return signature

    def get_common_name(self):
        """ read in our cert, and get our Common Name """
        with open(self.signer_cert_file, 'rb') as fh:
            cert = crypto.load_certificate(crypto.FILETYPE_PEM, fh.read())
        subject = cert.get_subject()
        return dict(subject.get_components())['CN']

    def _log_parsed_asn1(self, data):
        cmd = ['asn1parse', '-inform', 'DER' '-i']
        parsed_asn1 = openssl_command(cmd)
        log.debug(parsed_asn1)

    def _get_team_id(self):
        """ Same as Apple Organizational Unit. Should be in the cert """
        team_id = None
        cmd = [
            'x509',
            '-in', self.signer_cert_file,
            '-text',
            '-noout'
        ]
        certificate_info = openssl_command(cmd)
        subject_with_ou_match = re.compile(r'\s+Subject:.*OU=(\w+)')
        for line in certificate_info.splitlines():
            match = subject_with_ou_match.match(line)
            if match is not None:
                team_id = match.group(1)
                break
        return team_id
