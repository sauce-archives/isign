import binascii
import copy
import hashlib
import logging
from memoizer import memoize
import os
import plistlib
from plistlib import PlistWriter
import re

OUTPUT_DIRECTORY = '_CodeSignature'
OUTPUT_FILENAME = 'CodeResources'
TEMPLATE_FILENAME = 'code_resources_template.xml'
# DIGEST_ALGORITHM = "sha1"
HASH_BLOCKSIZE = 65536

log = logging.getLogger(__name__)


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

    def __init__(self, app_path, rules_data, respect_omissions=False):
        self.app_path = app_path
        self.app_dir = os.path.dirname(app_path)
        self.rules = []
        self.respect_omissions = respect_omissions
        for pattern, properties in rules_data.iteritems():
            self.rules.append(PathRule(pattern, properties))

    def find_rule(self, path):
        best_rule = ResourceBuilder.NULL_PATH_RULE
        for rule in self.rules:
            # log.debug('trying rule ' + str(rule) + ' against ' + path)
            if rule.matches(path):
                if rule.flags and rule.is_exclusion():
                    best_rule = rule
                    break
                elif rule.weight > best_rule.weight:
                    best_rule = rule
        return best_rule

    def get_rule_and_paths(self, root, path):
        path = os.path.join(root, path)
        relative_path = os.path.relpath(path, self.app_dir)
        rule = self.find_rule(relative_path)
        return (rule, path, relative_path)

    def scan(self):
        """
        Walk entire directory, compile mapping
        path relative to source_dir -> digest and other data
        """
        file_entries = {}
        # rule_debug_fmt = "rule: {0}, path: {1}, relative_path: {2}"
        for root, dirs, filenames in os.walk(self.app_dir):
            # log.debug("root: {0}".format(root))
            for filename in filenames:
                rule, path, relative_path = self.get_rule_and_paths(root,
                                                                    filename)
                # log.debug(rule_debug_fmt.format(rule, path, relative_path))

                if rule.is_exclusion():
                    continue

                if rule.is_omitted() and self.respect_omissions is True:
                    continue

                if self.app_path == path:
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

                if relative_path == OUTPUT_DIRECTORY:
                    dirs.remove(dirname)

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


@memoize
def get_hash_hex(path):
    """ Get the hash of a file at path, encoded as hexadecimal """
    hasher = hashlib.sha1()
    with open(path, 'rb') as afile:
        buf = afile.read(HASH_BLOCKSIZE)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(HASH_BLOCKSIZE)
    return hasher.hexdigest()


@memoize
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
    return output_path


def make_seal(source_app_path, target_dir=None):
    """
    Given a source app, create a CodeResources file for the
    surrounding directory, and write it into the appropriate path in a target
    directory
    """
    if target_dir is None:
        target_dir = os.path.dirname(source_app_path)
    template = get_template()
    # n.b. code_resources_template not only contains a template of
    # what the file should look like; it contains default rules
    # deciding which files should be part of the seal
    rules = template['rules2']
    plist = copy.deepcopy(template)
    resource_builder = ResourceBuilder(source_app_path, rules)
    plist['files'] = resource_builder.scan()
    resource_builder2 = ResourceBuilder(source_app_path, rules, True)
    plist['files2'] = resource_builder2.scan()
    return write_plist(target_dir, plist)
