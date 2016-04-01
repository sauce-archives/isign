from abc import ABCMeta
import biplist
import construct
# import copy
from exceptions import NotSignable
import hashlib
import logging
import macho_cs

log = logging.getLogger(__name__)


# See the documentation for an explanation of how
# CodeDirectory slots work.
class CodeDirectorySlot(object):
    __metaclass__ = ABCMeta
    offset = None

    def __init__(self, codesig):
        self.codesig = codesig

    def get_hash(self):
        return hashlib.sha1(self.get_contents()).digest()


class EntitlementsSlot(CodeDirectorySlot):
    offset = -5

    def get_contents(self):
        return self.codesig.get_blob_data('CSMAGIC_ENTITLEMENT')


class ApplicationSlot(CodeDirectorySlot):
    offset = -4

    def get_contents(self):
        return 0


class ResourceDirSlot(CodeDirectorySlot):
    offset = -3

    def __init__(self, seal_path):
        self.seal_path = seal_path

    def get_contents(self):
        return open(self.seal_path, "rb").read()


class RequirementsSlot(CodeDirectorySlot):
    offset = -2

    def get_contents(self):
        return self.codesig.get_blob_data('CSMAGIC_REQUIREMENTS')


class InfoSlot(CodeDirectorySlot):
    offset = -1

    def get_contents(self):
        # this will probably be similar to ResourceDir slot,
        # a hash of file contents
        raise "unimplemented"


#
# Represents a code signature object, aka the LC_CODE_SIGNATURE,
# within the Signable
#
class Codesig(object):
    """ wrapper around construct for code signature """
    def __init__(self, signable, data):
        self.signable = signable
        self.construct = macho_cs.Blob.parse(data)

    def build_data(self):
        return macho_cs.Blob.build(self.construct)

    def get_blob(self, magic):
        for index in self.construct.data.BlobIndex:
            if index.blob.magic == magic:
                return index.blob
        raise KeyError(magic)

    def get_blob_data(self, magic):
        """ convenience method, if we just want the data """
        blob = self.get_blob(magic)
        return macho_cs.Blob_.build(blob)

    def get_entitlements(self):
        """ returns a python object representing entitlements """
        try:
            entitlements = self.get_blob('CSMAGIC_ENTITLEMENT')
            # strip off two layers of wrapping. The Entitlement object has an adapter which
            # will ensure this is just a python object, no container
            return entitlements.data.data
        except KeyError:
            # NOTE: this library is focused on re-signing, but in the future, if we're
            # signing from scratch, return {} instead.
            raise NotSignable("expected {0} to have entitlements, found none")

    def write_entitlements(self, obj):
        """ takes python obj, creates equivalent entitlements and adds to codesig """
        # log.debug("entitlements:")
        try:
            entitlements = self.get_blob('CSMAGIC_ENTITLEMENT')
        except KeyError:
            raise NotSignable("expected {0} to have entitlements, found none")
        else:
            # make entitlements data if slot was found
            # libraries do not have entitlements data
            # so this is actually a difference between libs and apps
            # entitlements_data = macho_cs.Blob_.build(entitlements)
            # log.debug(hashlib.sha1(entitlements_data).hexdigest())
            entitlements.bytes = biplist.writePlistToString(obj, binary=False)
            entitlements.length = len(entitlements.bytes) + 8
            # entitlements_data = macho_cs.Blob_.build(entitlements)
            # log.debug(hashlib.sha1(entitlements_data).hexdigest())

    def update_entitlements(self, original_entitlements, team_id):
        """ Update entitlements to match entitlements in provisioning profile. """
        # TODO: Aborted design here to mutate entitlements from entitlements already
        # in the signable. The problem is that to resign properly, the entitlements
        # have to match what's in the provisioning profile exactly.
        #
        # The right design would be to figure out what entitlements the app needs,
        # and then use whatever remote API XCode uses to make a new PP with new
        # entitlements. OR: to have a very "maximal" set of entitlements in the
        # provisioning profile, and hope that they work with all incoming apps.
        #
        # For now, we are simply using a basic list of entitlements and *assuming*
        # they match the PP. They are, roughly:
        #   <?xml version="1.0" encoding="UTF-8"?>
        #   <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
        #             "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
        #   <plist version="1.0">
        #   <dict>
        #       <key>application-identifier</key>
        #       <string>YOUR_TEAM_ID.*</string>
        #       <key>com.apple.developer.team-identifier</key>
        #       <string>YOUR_TEAM_ID</string>
        #       <key>get-task-allow</key>
        #       <true/>
        #       <key>keychain-access-groups</key>
        #       <array>
        #           <string>YOUR_TEAM_ID.*</string>
        #       </array>
        #   </dict>
        #   </plist>
        #
        # I am keeping this design as it did eliminate the need for an external
        # entitlements file; now we can just have a python object representing
        # entitlements.

        # XXX throwing away original entitlements, see above
        # # make a copy so we don't mess with the original
        # entitlements = copy.deepcopy(original_entitlements)

        # XXX starting with an empty set of entitlements ensures we get the base set
        entitlements = {}

        # Utility functions to update various data structures in the entitlements.
        def replace_team_id_str(s):
            """ replace team id in a namespaced string, or simple string.
                e.g:
                    XXXXXXXX.tld.whatever.something --> TEAMID.tld.whatever.something
                    XXXXXXXX.* --> TEAMID.*
                    XXXXXXXX --> TEAMID
            """
            # Note we aren't looking for the old team id and replacing it.
            # We're forcing these keys to all be the same. (Sometimes customers
            # screw up and put different strings here.)
            components = s.split('.')
            components[0] = team_id
            return '.'.join(components)

        def replace_team_id(key):
            """ If corresponding key in `entitlements` exists, replace the team id.
                Otherwise use a default value. """
            val = entitlements[key]
            if isinstance(val, basestring):
                entitlements[key] = replace_team_id_str(val)
            elif isinstance(val, list):
                entitlements[key] = [replace_team_id_str(s) for s in val]
            else:
                log.error("did not recognize data structure: {0}".format(val))

        # iterate through all entitlements we care about. Stringwise replace the team
        # id if it already has a value. Otherwise, use a default value
        for key, default in [("com.apple.developer.team-identifier", team_id),
                             ("keychain-access-groups", [team_id + '.*']),
                             ("application-identifier", team_id + '.*')]:
            if key in entitlements:
                replace_team_id(key)
            else:
                entitlements[key] = default

        # If `com.apple.security.application-groups` in entitlements, ensure that
        # the value includes our Team ID. (Note: some customers have given apps to
        # us that have totally wrong values, don't even have their Team ID.)
        APP_GROUPS = "com.apple.security.application-groups"
        if APP_GROUPS in entitlements:
            # according to Apple's Entitlement Key References, the value must be
            # an array, with items that start with the Team ID plus a period plus
            # an arbitrary name.
            entitlements[APP_GROUPS] = [team_id + '.defaultappgroup']

        # The entitlement `get-task-allow` must be true for 'development' mode.
        # It allows debuggers to attach to the process. (It is unclear to me
        # whether that is necessary for Appium to work.)
        # TODO: Sauce Labs requires development mode, but it's possible that
        # others might want something different. So, make this configurable.
        entitlements["get-task-allow"] = True

        return entitlements

    def set_entitlements(self, signer):
        """ update entitlements with the signer's team id """
        entitlements = self.get_entitlements()
        entitlements = self.update_entitlements(entitlements, signer.team_id)
        self.write_entitlements(entitlements)

    def set_requirements(self, signer):
        # log.debug("requirements:")
        requirements = self.get_blob('CSMAGIC_REQUIREMENTS')
        # requirements_data = macho_cs.Blob_.build(requirements)
        # log.debug(hashlib.sha1(requirements_data).hexdigest())

        signer_cn = signer.get_common_name()

        # this is for convenience, a reference to the first blob
        # structure within requirements, which contains the data
        # we are going to change
        req_blob_0 = requirements.data.BlobIndex[0].blob
        req_blob_0_original_length = req_blob_0.length

        try:
            cn = req_blob_0.data.expr.data[1].data[1].data[0].data[2].Data
        except Exception:
            log.debug("no signer CN rule found in requirements")
            log.debug(requirements)
        else:
            # if we could find a signer CN rule, make requirements.

            # first, replace old signer CN with our own
            cn.data = signer_cn
            cn.length = len(cn.data)

            # req_blob_0 contains that CN, so rebuild it, and get what
            # the length is now
            req_blob_0.bytes = macho_cs.Requirement.build(req_blob_0.data)
            req_blob_0.length = len(req_blob_0.bytes) + 8

            # fix offsets of later blobs in requirements
            offset_delta = req_blob_0.length - req_blob_0_original_length
            for bi in requirements.data.BlobIndex[1:]:
                bi.offset += offset_delta

            # rebuild requirements, and set length for whole thing
            # TODO Entitlements??! Is this just because they are both plists?!
            requirements.bytes = macho_cs.Entitlements.build(requirements.data)
            requirements.length = len(requirements.bytes) + 8

        # then rebuild the whole data, but just to show the digest...?
        # requirements_data = macho_cs.Blob_.build(requirements)
        # log.debug(hashlib.sha1(requirements_data).hexdigest())

    def get_codedirectory(self):
        return self.get_blob('CSMAGIC_CODEDIRECTORY')

    def get_codedirectory_hash_index(self, slot):
        """ The slots have negative offsets, because they start from the 'top'.
            So to get the actual index, we add it to the length of the
            slots. """
        return slot.offset + self.get_codedirectory().data.nSpecialSlots

    def has_codedirectory_slot(self, slot):
        """ Some dylibs have all 5 slots, even though technically they only need
            the first 2. If this dylib only has 2 slots, some of the calculated
            indices for slots will be negative. This means we don't do
            those slots when resigning (for dylibs, they don't add any
            security anyway) """
        return self.get_codedirectory_hash_index(slot) >= 0

    def fill_codedirectory_slot(self, slot):
        if self.signable.should_fill_slot(slot):
            index = self.get_codedirectory_hash_index(slot)
            self.get_codedirectory().data.hashes[index] = slot.get_hash()

    def set_codedirectory(self, seal_path, signer):
        if self.has_codedirectory_slot(EntitlementsSlot):
            self.fill_codedirectory_slot(EntitlementsSlot(self))

        if self.has_codedirectory_slot(ResourceDirSlot):
            self.fill_codedirectory_slot(ResourceDirSlot(seal_path))

        if self.has_codedirectory_slot(RequirementsSlot):
            self.fill_codedirectory_slot(RequirementsSlot(self))

        cd = self.get_codedirectory()
        cd.data.teamID = signer.team_id

        cd.bytes = macho_cs.CodeDirectory.build(cd.data)
        # cd_data = macho_cs.Blob_.build(cd)
        # log.debug(len(cd_data))
        # open("cdrip", "wb").write(cd_data)
        # log.debug("CDHash:" + hashlib.sha1(cd_data).hexdigest())

    def set_signature(self, signer):
        # TODO how do we even know this blobwrapper contains the signature?
        # seems like this is a coincidence of the structure, where
        # it's the only blobwrapper at that level...
        # log.debug("sig:")
        sigwrapper = self.get_blob('CSMAGIC_BLOBWRAPPER')
        # oldsig = sigwrapper.bytes.value
        # signer._log_parsed_asn1(sigwrapper.data.data.value)
        # open("sigrip.der", "wb").write(sigwrapper.data.data.value)
        cd_data = self.get_blob_data('CSMAGIC_CODEDIRECTORY')
        sig = signer.sign(cd_data)
        # log.debug("sig len: {0}".format(len(sig)))
        # log.debug("old sig len: {0}".format(len(oldsig)))
        # open("my_sigrip.der", "wb").write(sig)
        sigwrapper.data = construct.Container(data=sig)
        # signer._log_parsed_asn1(sig)
        # sigwrapper.data = construct.Container(data="hahaha")
        sigwrapper.length = len(sigwrapper.data.data) + 8
        sigwrapper.bytes = sigwrapper.data.data
        # log.debug(len(sigwrapper.bytes))

    def update_offsets(self):
        # update section offsets, to account for any length changes
        offset = self.construct.data.BlobIndex[0].offset
        for blob in self.construct.data.BlobIndex:
            blob.offset = offset
            offset += len(macho_cs.Blob.build(blob.blob))

        superblob = macho_cs.SuperBlob.build(self.construct.data)
        self.construct.length = len(superblob) + 8
        self.construct.bytes = superblob

    def resign(self, bundle, signer):
        """ Do the actual signing. Create the structre and then update all the
            byte offsets """
        if self.signable.needs_entitlements:
            self.set_entitlements(signer)
        self.set_requirements(signer)
        # See docs/codedirectory.rst for some notes on optional hashes
        self.set_codedirectory(bundle.seal_path, signer)
        self.set_signature(signer)
        self.update_offsets()

    # TODO make this optional, in case we want to check hashes or something
    # log.debug(hashes)
    # cd = codesig_cons.data.BlobIndex[0].blob.data
    # end_offset = arch_macho.macho_start + cd.codeLimit
    # start_offset = ((end_offset + 0xfff) & ~0xfff) - (cd.nCodeSlots * 0x1000)

    # for i in xrange(cd.nSpecialSlots):
    #    expected = cd.hashes[i]
    #    log.debug("special exp=%s" % expected.encode('hex'))

    # for i in xrange(cd.nCodeSlots):
    #     expected = cd.hashes[cd.nSpecialSlots + i]
    #     f.seek(start_offset + 0x1000 * i)
    #     actual_data = f.read(min(0x1000, end_offset - f.tell()))
    #     actual = hashlib.sha1(actual_data).digest()
    #     log.debug('[%s] exp=%s act=%s' % ()
    #         ('bad', 'ok ')[expected == actual],
    #         expected.encode('hex'),
    #         actual.encode('hex')
    #     )
