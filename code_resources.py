import binascii
import copy
# import distutils
import hashlib
from optparse import OptionParser
import os
import plistlib
from plistlib import PlistWriter
import re
# import subprocess

OUTPUT_DIRECTORY = '_CodeSignature'
OUTPUT_FILENAME = 'CodeResources'
TEMPLATE_FILENAME = 'code_resources_template.xml'
# DIGEST_ALGORITHM = "sha1"
HASH_BLOCKSIZE = 65536

# OPENSSL = os.getenv('OPENSSL', distutils.spawn.find_executable('openssl'))


# have to monkey patch Plist, in order to make the values
# look the same - no .0 for floats
# Apple's plist utils work like this:
#   1234.5 --->  <real>1234.5</real>
#   1234.0 --->  <real>1234</real>
def writeValue(self, value):
    if isinstance(value, float):
        rep = repr(value)
        if value.is_integer():
            rep = repr(int(value))
        self.simpleElement("real", rep)
    else:
        self.oldWriteValue(value)

PlistWriter.oldWriteValue = PlistWriter.writeValue
PlistWriter.writeValue = writeValue


# Simple reimplementation of ResourceBuilder, in the Apple Open Source
# file bundlediskrep.cpp
class PathRule(object):
    OPTIONAL = 0x01
    OMITTED = 0x02
    NESTED = 0x04
    EXCLUSION = 0x10  # unused?
    TOP = 0x20        # unused?

    def __init__(self, pattern='', properties=None):
        # on Mac OS the FS is case-insensitive; simulate that here
        self.pattern = re.compile(pattern, re.IGNORECASE)
        self.flags = 0
        self.weight = 0
        if properties is not None:
            if type(properties) == 'bool':
                if properties is False:
                    self.flags |= PathRule.OMITTED
                # if it was true, this file is required;
                # do nothing
            elif isinstance(properties, dict):
                for key, value in properties.iteritems():
                    if key == 'optional' and value is True:
                        self.flags |= PathRule.OPTIONAL
                    elif key == 'omit' and value is True:
                        self.flags |= PathRule.OMITTED
                    elif key == 'nested' and value is True:
                        self.flags |= PathRule.NESTED
                    elif key == 'weight':
                        self.weight = float(value)

    def is_optional(self):
        return self.flags & PathRule.OPTIONAL != 0

    def is_omitted(self):
        return self.flags & PathRule.OMITTED != 0

    def is_nested(self):
        return self.flags & PathRule.NESTED != 0

    def is_exclusion(self):
        return self.flags & PathRule.EXCLUSION != 0

    def is_top(self):
        return self.flags & PathRule.TOP != 0

    def matches(self, path):
        return re.match(self.pattern, path)

    def __str__(self):
        return 'PathRule:' + str(self.flags) + ':' + str(self.weight)


class ResourceBuilder(object):
    NULL_PATH_RULE = PathRule()

    def __init__(self, rules_data):
        self.rules = []
        for pattern, properties in rules_data.iteritems():
            self.rules.append(PathRule(pattern, properties))

    def find_rule(self, path):
        best_rule = ResourceBuilder.NULL_PATH_RULE
        for rule in self.rules:
            # print 'trying rule ' + str(rule) + ' against ' + path
            if rule.matches(path):
                if rule.flags and rule.is_exclusion():
                    best_rule = rule
                    break
                elif rule.weight > best_rule.weight:
                    best_rule = rule
        return best_rule

    def get_rule_and_paths(self, root, path):
        path = os.path.join(root, path)
        relative_path = os.path.relpath(path, source_dir)
        rule = self.find_rule(relative_path)
        return (rule, path, relative_path)

    def scan(self, source_dir):
        """
        Walk entire directory, compile mapping
        path relative to source_dir -> digest and other data
        """
        file_entries = {}
        for root, dirs, filenames in os.walk(source_dir):

            for filename in filenames:
                rule, path, relative_path = self.get_rule_and_paths(root,
                                                                    filename)

                if rule.is_omitted() or rule.is_exclusion():
                    continue

                # the Data element in plists is base64-encoded
                val = {'hash': plistlib.Data(get_hash_binary(path))}

                if rule.is_optional():
                    val['optional'] = True

                if len(val) == 1 and 'hash' in val:
                    file_entries[relative_path] = val['hash']
                else:
                    file_entries[relative_path] = val

            for dirname in dirs:
                rule, path, relative_path = self.get_rule_and_paths(root,
                                                                    dirname)

                if rule.is_nested() and '.' not in path:
                    dirs.remove(dirname)
                    continue

        return file_entries


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
    resource_builder = ResourceBuilder(rules)
    plist['files'] = resource_builder.scan(source_dir)
    write_plist(target_dir, plist)


if __name__ == '__main__':
    parser = OptionParser()
    options, args = parser.parse_args()
    source_dir, target_dir = args
    main(source_dir, target_dir)
