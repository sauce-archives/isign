#
# Small object that can be passed around easily, that represents
# our signing credentials, and can sign data.
#
# TODO should we be using PyOpenSSL rather than piping to openssl?

import distutils
import logging
import os
import os.path
import subprocess
import re

OPENSSL = os.getenv('OPENSSL', distutils.spawn.find_executable('openssl'))

log = logging.getLogger(__name__)


class Signer(object):
    """ collaborator, holds the keys, identifiers for signer,
        and knows how to sign data """
    def __init__(self,
                 signer_key_file=None,
                 signer_cert_file=None,
                 apple_cert_file=None,
                 team_id=None):
        """ signer_key_file = your org's .p12
            signer_cert_file = your org's .pem
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

    def sign(self, data):
        """ sign data, return filehandle """
        proc = subprocess.Popen("%s cms"
                                " -sign -binary -nosmimecap"
                                " -certfile %s"
                                " -signer %s"
                                " -inkey %s"
                                " -keyform pkcs12 "
                                " -outform DER" %
                                (OPENSSL,
                                 self.apple_cert_file,
                                 self.signer_cert_file,
                                 self.signer_key_file),
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                shell=True)
        proc.stdin.write(data)
        out, err = proc.communicate()
        log.debug(err)
        return out

    def _log_parsed_asn1(self, data):
        proc = subprocess.Popen('%s asn1parse -inform DER -i' % (OPENSSL),
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                shell=True)
        proc.stdin.write(data)
        out, err = proc.communicate()
        log.debug(out)

    def _get_team_id(self):
        """ Same as Apple Organizational Unit. Should be in the cert """
        team_id = None
        cmd = [
            OPENSSL,
            'x509',
            '-in', self.signer_cert_file,
            '-text',
            '-noout'
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        out, err = proc.communicate()
        subject_with_ou_match = re.compile(r'\s+Subject:.*OU=(\w+)')
        for line in out.splitlines():
            match = subject_with_ou_match.match(line)
            if match is not None:
                team_id = match.group(1)
                break
        return team_id
