import construct
import hashlib
import macho_cs
import OpenSSL


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

    def set_entitlements(self, entitlements_path):
        print "entitlements:"
        entitlements_data = None
        try:
            entitlements = self.get_blob('CSMAGIC_ENTITLEMENT')
        except KeyError:
            print "no entitlements found"
        else:
            # make entitlements data if slot was found
            # libraries do not have entitlements data
            # so this is actually a difference between libs and apps
            entitlements_data = macho_cs.Blob_.build(entitlements)
            print hashlib.sha1(entitlements_data).hexdigest()

            entitlements.bytes = open(entitlements_path, "rb").read()
            entitlements.length = len(entitlements.bytes) + 8
            entitlements_data = macho_cs.Blob_.build(entitlements)
            print hashlib.sha1(entitlements_data).hexdigest()

        print

    def set_requirements(self, signer):
        print "requirements:"
        requirements = self.get_blob('CSMAGIC_REQUIREMENTS')
        requirements_data = macho_cs.Blob_.build(requirements)
        print hashlib.sha1(requirements_data).hexdigest()

        # read in our cert, and get our Common Name
        signer_key_data = open(signer.signer_key_file, "rb").read()
        signer_p12 = OpenSSL.crypto.load_pkcs12(signer_key_data)
        subject = signer_p12.get_certificate().get_subject()
        signer_cn = dict(subject.get_components())['CN']

        # this is for convenience, a reference to the first blob
        # structure within requirements, which contains the data
        # we are going to change
        req_blob_0 = requirements.data.BlobIndex[0].blob
        req_blob_0_original_length = req_blob_0.length

        try:
            cn = req_blob_0.data.expr.data[1].data[1].data[0].data[2].Data
        except Exception:
            print "no signer CN rule found in requirements"
            print requirements
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
            requirements.bytes = macho_cs.Entitlements.build(requirements.data)
            requirements.length = len(requirements.bytes) + 8

        # then rebuild the whole data, but just to show the digest...?
        requirements_data = macho_cs.Blob_.build(requirements)
        print hashlib.sha1(requirements_data).hexdigest()
        print

    def set_codedirectory(self, seal_path, signer):
        print "code directory:"
        cd = self.get_blob('CSMAGIC_CODEDIRECTORY')
        # print cd

        # The codedirectory contains "slots" for special hashes.
        # These slots are different between executable and dylib
        slots = self.signable.get_codedirectory_special_slots()
        assert cd.data.nSpecialSlots == len(slots)

        # the slots are all negative offsets, matching what's in
        # codedirectory.h. We add the slots length to get positive subscripts
        # again. It will all work out in the end.
        if 'cdEntitlementSlot' in slots:
            hashnum = slots['cdEntitlementSlot'] + len(slots)
            # this is an app, so by now we should have this
            entitlements_data = self.get_blob_data('CSMAGIC_ENTITLEMENT')
            cd.data.hashes[hashnum] = hashlib.sha1(entitlements_data).digest()

        if 'cdResourceDirSlot' in slots:
            hashnum = slots['cdResourceDirSlot'] + len(slots)
            seal_contents = open(seal_path, "rb").read()
            cd.data.hashes[hashnum] = hashlib.sha1(seal_contents).digest()

        if 'cdRequirementsSlot' in slots:
            hashnum = slots['cdRequirementsSlot'] + len(slots)
            requirements_data = self.get_blob_data('CSMAGIC_REQUIREMENTS')
            cd.data.hashes[hashnum] = hashlib.sha1(requirements_data).digest()

        cd.data.teamID = signer.team_id

        cd.bytes = macho_cs.CodeDirectory.build(cd.data)
        cd_data = macho_cs.Blob_.build(cd)
        print len(cd_data)
        # open("cdrip", "wb").write(cd_data)
        print "CDHash:", hashlib.sha1(cd_data).hexdigest()
        print

    def set_signature(self, signer):
        # TODO how do we even know this blobwrapper contains the signature?
        # seems like this is a coincidence of the structure, where
        # it's the only blobwrapper at that level...
        print "sig:"
        sigwrapper = self.get_blob('CSMAGIC_BLOBWRAPPER')
        oldsig = sigwrapper.bytes.value
        # signer._print_parsed_asn1(sigwrapper.data.data.value)
        # open("sigrip.der", "wb").write(sigwrapper.data.data.value)
        cd_data = self.get_blob_data('CSMAGIC_CODEDIRECTORY')
        sig = signer.sign(cd_data)
        print "sig len:", len(sig)
        print "old sig len:", len(oldsig)
        # open("my_sigrip.der", "wb").write(sig)
        # print hexdump(oldsig)
        sigwrapper.data = construct.Container(data=sig)
        # signer._print_parsed_asn1(sig)
        # sigwrapper.data = construct.Container(data="hahaha")
        sigwrapper.length = len(sigwrapper.data.data) + 8
        sigwrapper.bytes = sigwrapper.data.data
        # print len(sigwrapper.bytes)
        # print hexdump(sigwrapper.bytes)
        print

    def update_offsets(self):
        # update section offsets, to account for any length changes
        offset = self.construct.data.BlobIndex[0].offset
        for blob in self.construct.data.BlobIndex:
            blob.offset = offset
            offset += len(macho_cs.Blob.build(blob.blob))

        superblob = macho_cs.SuperBlob.build(self.construct.data)
        self.construct.length = len(superblob) + 8
        self.construct.bytes = superblob

    def resign(self, app, signer):
        self.set_entitlements(app.entitlements_path)
        self.set_requirements(signer)
        self.set_codedirectory(app.seal_path, signer)
        self.set_signature(signer)
        self.update_offsets()

    # TODO make this optional, in case we want to check hashes or something
    # print hashes
    # cd = codesig_cons.data.BlobIndex[0].blob.data
    # end_offset = arch_macho.macho_start + cd.codeLimit
    # start_offset = ((end_offset + 0xfff) & ~0xfff) - (cd.nCodeSlots * 0x1000)

    # for i in xrange(cd.nSpecialSlots):
    #    expected = cd.hashes[i]
    #    print "special exp=%s" % expected.encode('hex')

    # for i in xrange(cd.nCodeSlots):
    #     expected = cd.hashes[cd.nSpecialSlots + i]
    #     f.seek(start_offset + 0x1000 * i)
    #     actual_data = f.read(min(0x1000, end_offset - f.tell()))
    #     actual = hashlib.sha1(actual_data).digest()
    #     print '[%s] exp=%s act=%s' % (
    #         ('bad', 'ok ')[expected == actual],
    #         expected.encode('hex'),
    #         actual.encode('hex')
    #     )
