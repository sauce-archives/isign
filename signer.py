#
# Small object that can be passed around easily, that represents
# our signing credentials, and can sign data.
#

import distutils
import os
import subprocess

OPENSSL = os.getenv('OPENSSL', distutils.spawn.find_executable('openssl'))


class Signer(object):
    """ collaborator, holds the keys and knows how to sign data """
    def __init__(self,
                 signer_key_file=None,
                 signer_cert_file=None,
                 apple_cert_file=None):
        """ signer_key_file = your org's .p12
            signer_cert_file = your org's .pem
            apple_cert_file = apple certs in .pem form """
        self.signer_key_file = signer_key_file
        self.signer_cert_file = signer_cert_file
        self.apple_cert_file = apple_cert_file

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
        print err
        return out

    def _print_parsed_asn1(self, data):
        proc = subprocess.Popen('%s asn1parse -inform DER -i' % (OPENSSL),
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                shell=True)
        proc.stdin.write(data)
        out, err = proc.communicate()
        print out
