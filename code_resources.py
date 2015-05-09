import base64
import binascii
import copy
# import distutils
import hashlib
from optparse import OptionParser
import os
import plistlib
# import re
# import subprocess

OUTPUT_DIRECTORY = '_CodeSignature'
OUTPUT_FILENAME = 'CodeResources'
TEMPLATE_FILENAME = 'code_resources_template.xml'
DIGEST_ALGORITHM = "sha1"
HASH_BLOCKSIZE = 65536

# OPENSSL = os.getenv('OPENSSL', distutils.spawn.find_executable('openssl'))


def get_template():
    """
    Obtain the 'template' plist which also contains things like
    default rules about which files should count
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(current_dir, TEMPLATE_FILENAME)
    fh = open(template_path, 'r')
    return plistlib.readPlist(fh)


def encode(hex_string):
    sha1_binary = binascii.a2b_hex(hex_string)
    return base64.b64encode(sha1_binary)


def get_digest(path):
    hasher = hashlib.sha1()
    with open(path, 'rb') as afile:
        buf = afile.read(HASH_BLOCKSIZE)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(HASH_BLOCKSIZE)
    return hasher.hexdigest()


# def get_digest(path):
#     """
#     Get the digest of a file.
#
#     Piping to the openssl binary seems to be the fastest
#     """
#     proc = subprocess.Popen([OPENSSL, DIGEST_ALGORITHM, path],
#                             stdout=subprocess.PIPE,
#                             stderr=subprocess.PIPE)
#     out, err = proc.communicate()
#     if proc.returncode != 0:
#         print "returncode from proc = {0}".format(proc.returncode)
#     if err != "":
#         print "error hashing: <{0}>".format(err)
#     # output line looks like
#     # SHA1(yourfile)= 53aad19d86fe01a0e569951d6772105860bf425c
#     return re.split(r'\s+', out)[1]


def get_digests(source_dir, rules):
    """
    Walk entire directory, compile mapping
    path relative to source_dir -> digest

    in this file format, hashes are base64(integer sha1)
    """
    digests = {}
    for root, dirs, files in os.walk(source_dir):
        for filename in files:
            path = os.path.join(root, filename)
            relpath_to_source = os.path.relpath(path, source_dir)
            digests[relpath_to_source] = encode(get_digest(path))
    return digests


def write_file(target_dir, output):
    output_dir = os.path.join(target_dir, OUTPUT_DIRECTORY)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    output_path = os.path.join(output_dir, OUTPUT_FILENAME)
    fh = open(output_path, 'w')
    plistlib.writePlist(output, fh)


def main(source_dir, target_dir):
    template = get_template()
    # n.b. code_resources_template not only contains a template of
    # what the file should look like; it contains default rules
    # deciding which files should be part of the seal
    rules = template['rules2']
    output = copy.deepcopy(template)
    output['files'] = get_digests(source_dir, rules)
    write_file(target_dir, output)


if __name__ == '__main__':
    parser = OptionParser()
    options, args = parser.parse_args()
    source_dir, target_dir = args
    main(source_dir, target_dir)
