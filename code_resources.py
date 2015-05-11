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


# def get_hash(path):
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


def get_hash_hex(path):
    """ Get the hash of a file at path, encoded as hexadecimal """
    hasher = hashlib.sha1()
    with open(path, 'rb') as afile:
        buf = afile.read(HASH_BLOCKSIZE)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(HASH_BLOCKSIZE)
    return hasher.hexdigest()


def get_hash_binary(path):
    """ Get the hash of a file at path, encoded as binary """
    return binascii.a2b_hex(get_hash_hex(path))


def is_optional(path, rules):
    return 'Assets.car' not in path


def get_file_entries(source_dir, rules):
    """
    Walk entire directory, compile mapping
    path relative to source_dir -> digest and other data
    """
    file_entries = {}
    for root, dirs, filenames in os.walk(source_dir):
        for filename in filenames:
            path = os.path.join(root, filename)
            # the Data element in plists is base64-encoded
            data = plistlib.Data(get_hash_binary(path))
            relpath_to_source = os.path.relpath(path, source_dir)
            if is_optional(path, rules):
                val = {
                    'data': data,
                    'optional': True
                }
            else:
                val = data
            file_entries[relpath_to_source] = val
    return file_entries


def write_plist(target_dir, plist):
    """ Write the CodeResources file """
    output_dir = os.path.join(target_dir, OUTPUT_DIRECTORY)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    output_path = os.path.join(output_dir, OUTPUT_FILENAME)
    fh = open(output_path, 'w')
    plistlib.writePlist(plist, fh)


def main(source_dir, target_dir):
    """
    Given a source directory, create a CodeResources file for that
    directory, and write it into the appropriate path in a target
    directory
    """
    template = get_template()
    # n.b. code_resources_template not only contains a template of
    # what the file should look like; it contains default rules
    # deciding which files should be part of the seal
    rules = template['rules2']
    plist = copy.deepcopy(template)
    plist['files'] = get_file_entries(source_dir, rules)
    write_plist(target_dir, plist)


if __name__ == '__main__':
    parser = OptionParser()
    options, args = parser.parse_args()
    source_dir, target_dir = args
    main(source_dir, target_dir)
