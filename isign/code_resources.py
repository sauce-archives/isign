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

    def __init__(self,
                 app_path,
                 rules_data,
                 respect_omissions=False,
                 sha256=False):
        # TODO unify this with our concept of bundles now
        self.app_path = app_path
        self.app_dir = os.path.dirname(app_path)

        self.respect_omissions = respect_omissions

        # Decide which hash digests to include for each file, and what they
        # will be called in the data structure.
        #
        # This is a mapping of the name the hash will have in the XML file,
        # to the hash method to be used.
        #
        # Apple used to simply call the sha1 the 'hash'. Now in the files2
        # section they also include the sha256, so they called that 'hash2'.
        self.hash_methods = {'hash': hashlib.sha1}
        if sha256:
            self.hash_methods['hash2'] = hashlib.sha256

        self.rules = []
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
        path relative to source_dir -> hash digests and other data
        """
        file_entries = {}
        # rule_debug_fmt = "rule: {0}, path: {1}, relative_path: {2}"
        for root, dirs, filenames in os.walk(self.app_dir):
            # log.debug("root: {0}".format(root))
            for filename in filenames:
                rule, path, relative_path = self.get_rule_and_paths(root,
                                                                    filename)
                # log.debug(rule_debug_fmt.format(rule, path, relative_path))

                # skip this file if the rule for this path is to exclude
                if rule.is_exclusion():
                    continue

                # skip this file if the rule for this path is to omit
                if rule.is_omitted() and self.respect_omissions is True:
                    continue

                # skip this file if the path is the main application
                # TODO reconcile with the bundle.executable idea
                if self.app_path == path:
                    continue

                # Okay, we're going to make a value for this file...
                val = {}

                # Get binary hashes about this file. We expect this to contain
                # a dictionary of hash method to binary hash digest.
                hash_digests = get_hash_digests(path)

                # Encode the hashes.
                # We wrap the binary hashes in the plist Data type.
                # Depending on which section, we may not use all the hashes;
                # we only use the hashes listed in self.hash_methods.
                for key, hash_method in self.hash_methods.iteritems():
                    if hash_method not in hash_digests:
                        raise Exception("Expected hash digest missing")
                    val[key] = plistlib.Data(hash_digests[hash_method])

                if rule.is_optional():
                    val['optional'] = True

                # if there's only one, non-optional hash, unwrap it from the dict
                if len(val) == 1 and 'optional' not in val:
                    val = val.values()[0]

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


@memoize
def get_hash_digests(path):
    """ Get several hashes of a file at path, encoded as binary """
    # Since we don't want to read in files multiple times, we get
    # all the hash algorithms we'll want. We also memoize the data
    # because we'll be getting these digests several times for
    # different parts of the emitted data.

    # initialize the hashers, e.g. sha1, sha256, etc
    sha1_hasher = hashlib.sha1()
    sha256_hasher = hashlib.sha256()

    # do all the hashing of this file
    with open(path, 'rb') as afile:
        while True:
            buf = afile.read(HASH_BLOCKSIZE)
            sha1_hasher.update(buf)
            sha256_hasher.update(buf)
            if len(buf) == 0:
                break

    # return a dictionary of hash methods to hash digests
    return {hashlib.sha1: sha1_hasher.digest(),
            hashlib.sha256: sha256_hasher.digest()}


def get_template():
    """
    Obtain the 'template' plist which also contains things like
    default rules about which files should count
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(current_dir, TEMPLATE_FILENAME)
    fh = open(template_path, 'r')
    return plistlib.readPlist(fh)


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
    resource_builder2 = ResourceBuilder(source_app_path, rules, True, True)
    plist['files2'] = resource_builder2.scan()
    return write_plist(target_dir, plist)
