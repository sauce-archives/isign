import biplist
import construct
import distutils
import hashlib
import isign
import subprocess
import os
import OpenSSL
# from hexdump import hexdump

import macho
import macho_cs


OPENSSL = os.getenv('OPENSSL', distutils.spawn.find_executable('openssl'))

# in Entitlement plists
TEAM_IDENTIFIER_KEY = 'com.apple.developer.team-identifier'


def get_team_id(entitlements_file):
    # TODO obtain this from entitlements
    entitlements_plist = biplist.readPlist(entitlements_file)
    return entitlements_plist[TEAM_IDENTIFIER_KEY]


class Signer(object):
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


class Codesig(object):
    """ wrapper around construct for code signature """
    def __init__(self, construct):
        self.construct = construct

    def get_blob(self, magic):
        for index in self.construct.data.BlobIndex:
            if index.blob.magic == magic:
                return index.blob
        raise KeyError(magic)

    def get_blob_data(self, magic):
        """ convenience method, if we just want the data """
        blob = self.get_blob(magic)
        return macho_cs.Blob_.build(blob)

    def set_entitlements(self, entitlements_file):
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

            entitlements.bytes = open(entitlements_file, "rb").read()
            entitlements.length = len(entitlements.bytes) + 8
            entitlements_data = macho_cs.Blob_.build(entitlements)
            print hashlib.sha1(entitlements_data).hexdigest()

        print

    def set_requirements(self, signer):
        print "requirements:"
        requirements = self.get_blob('CSMAGIC_REQUIREMENTS')
        requirements_data = macho_cs.Blob_.build(requirements)
        print hashlib.sha1(requirements_data).hexdigest()
        signer_key_data = open(signer.signer_key_file, "rb").read()
        signer_p12 = OpenSSL.crypto.load_pkcs12(signer_key_data)
        subject = signer_p12.get_certificate().get_subject()
        signer_cn = dict(subject.get_components())['CN']
        try:
            cn = requirements.data.BlobIndex[0].blob.data.expr.data[1].data[1].data[0].data[2].Data
        except Exception:
            print "no signer CN rule found in requirements"
            print requirements
        else:
            # if we could find a signer CN rule, make requirements
            cn.data = signer_cn
            cn.length = len(cn.data)
            old_len = requirements.data.BlobIndex[0].blob.length
            requirements.data.BlobIndex[0].blob.bytes = macho_cs.Requirement.build(requirements.data.BlobIndex[0].blob.data)
            requirements.data.BlobIndex[0].blob.length = len(requirements.data.BlobIndex[0].blob.bytes) + 8
            for bi in requirements.data.BlobIndex[1:]:
                bi.offset -= old_len
                bi.offset += requirements.data.BlobIndex[0].blob.length
            requirements.bytes = macho_cs.Entitlements.build(requirements.data)
            requirements.length = len(requirements.bytes) + 8
        # TODO why do we rebuild the data? even if we didn't change it?
        requirements_data = macho_cs.Blob_.build(requirements)
        print hashlib.sha1(requirements_data).hexdigest()
        print

    def set_codedirectory(self, seal_file, team_id):
        print "code directory:"
        cd = self.get_blob('CSMAGIC_CODEDIRECTORY')
        # print cd
        hashnum = 0
        # if this is an app, add the entitlements and seal hash
        if cd.data.nSpecialSlots == 5:
            # this is an app, so by now we should have this
            entitlements_data = self.get_blob_data('CSMAGIC_ENTITLEMENT')
            cd.data.hashes[hashnum] = hashlib.sha1(entitlements_data).digest()
            hashnum += 2
            seal_contents = open(seal_file, "rb").read()
            cd.data.hashes[hashnum] = hashlib.sha1(seal_contents).digest()
            hashnum += 1
        else:
            # this is a library, should have 2 special slots
            assert cd.data.nSpecialSlots == 2
        requirements_data = self.get_blob_data('CSMAGIC_REQUIREMENTS')
        cd.data.hashes[hashnum] = hashlib.sha1(requirements_data).digest()
        cd.data.teamID = team_id
        cd.bytes = macho_cs.CodeDirectory.build(cd.data)
        cd_data = macho_cs.Blob_.build(cd)
        print len(cd_data)
        # open("cdrip", "wb").write(cd_data)
        print "CDHash:", hashlib.sha1(cd_data).hexdigest()
        print

    def _print_parsed_asn1(self, data):
        proc = subprocess.Popen('openssl asn1parse -inform DER -i',
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                shell=True)
        proc.stdin.write(data)
        out, err = proc.communicate()
        print out

    def set_signature(self, signer):
        # TODO how do we even know this blobwrapper contains the signature?
        # seems like this is a coincidence of the structure, where
        # it's the only blobwrapper at that level...
        print "sig:"
        sigwrapper = self.get_blob('CSMAGIC_BLOBWRAPPER')
        oldsig = sigwrapper.bytes.value
        # self._print_parsed_asn1(sigwrapper.data.data.value)
        # open("sigrip.der", "wb").write(sigwrapper.data.data.value)
        cd_data = self.get_blob_data('CSMAGIC_CODEDIRECTORY')
        sig = signer.sign(cd_data)
        print "sig len:", len(sig)
        print "old sig len:", len(oldsig)
        # open("my_sigrip.der", "wb").write(sig)
        # print hexdump(oldsig)
        sigwrapper.data = construct.Container(data=sig)
        # self._print_parsed_asn1(sig)
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

    def resign(self,
               entitlements_file,
               seal_file,
               signer,
               team_id):
        self.set_entitlements(entitlements_file)
        self.set_requirements(signer)
        self.set_codedirectory(seal_file, team_id)
        self.set_signature(signer)
        self.update_offsets()


def sign_architecture(arch_macho,
                      arch_end,
                      f,
                      entitlements_file,
                      seal_file,
                      signer,
                      team_id):
    cmds = {}
    for cmd in arch_macho.commands:
        name = cmd.cmd
        cmds[name] = cmd

    if 'LC_CODE_SIGNATURE' in cmds:
        lc_cmd = cmds['LC_CODE_SIGNATURE']
        # re-sign
        print "re-signing"
        codesig_offset = arch_macho.macho_start + lc_cmd.data.dataoff
        f.seek(codesig_offset)
        codesig_data = f.read(lc_cmd.data.datasize)
        # print len(codesig_data)
        # print hexdump(codesig_data)
        codesig_cons = macho_cs.Blob.parse(codesig_data)
    else:
        # TODO: this doesn't actually work :(
        isign.make_signature(arch_macho, arch_end, cmds, f, entitlements_file)
        # TODO get the construct back from this method as codesig_cons

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

    codesig = Codesig(codesig_cons)
    codesig.resign(entitlements_file,
                   seal_file,
                   signer,
                   team_id)

    # print new_codesig_cons
    new_codesig_data = macho_cs.Blob.build(codesig.construct)
    print "old len:", len(codesig_data)
    print "new len:", len(new_codesig_data)

    new_codesig_data += "\x00" * (len(codesig_data) - len(new_codesig_data))
    print "padded len:", len(new_codesig_data)
    print "----"
    # print hexdump(new_codesig_data)
    # assert new_codesig_data != codesig_data

    lc_cmd = cmds['LC_CODE_SIGNATURE']
    lc_cmd.data.datasize = len(new_codesig_data)
    lc_cmd.bytes = macho.CodeSigRef.build(cmd.data)

    offset = lc_cmd.data.dataoff
    return offset, new_codesig_data


def sign_file(filename, entitlements_file, signer):
    # not all files need the entitlements data, but we use
    # it here as a config file to get our team id
    team_id = get_team_id(entitlements_file)

    print "working on {0}".format(filename)

    # TODO this is WRONG if the file is a dylib, but it doesn't matter b/c
    # we don't use the seal_file in that case. Need to untangle
    app_dir = os.path.dirname(filename)
    seal_file = os.path.join(app_dir, '_CodeSignature/CodeResources')

    f = open(filename, "rb")
    m = macho.MachoFile.parse_stream(f)
    arch_macho = m.data
    f.seek(0, os.SEEK_END)
    file_end = f.tell()
    arches = []
    if 'FatArch' in arch_macho:
        for i, arch in enumerate(arch_macho.FatArch):
            a = {'macho': arch.MachO}
            next_macho = i + 1
            if next_macho == len(arch_macho.FatArch):  # last
                a['macho_end'] = file_end
            else:
                next_arch = arch_macho.FatArch[next_macho]
                a['macho_end'] = next_arch.MachO.macho_start
            arches.append(a)
    else:
        arches.append({'macho': arch_macho, 'macho_end': file_end})

    # copy f into outfile, reset to beginning of file
    outfile = open("foo", "wb")
    f.seek(0)
    outfile.write(f.read())
    outfile.seek(0)

    # write new codesign blocks for each arch
    offset_fmt = "offset: {2}, write offset: {0}, new_codesig_data len: {1}"
    for arch in arches:
        offset, new_codesig_data = sign_architecture(arch['macho'],
                                                     arch['macho_end'],
                                                     f,
                                                     entitlements_file,
                                                     seal_file,
                                                     signer,
                                                     team_id)
        write_offset = arch['macho'].macho_start + offset
        print offset_fmt.format(write_offset, len(new_codesig_data), offset)
        outfile.seek(write_offset)
        outfile.write(new_codesig_data)

    # write new headers
    outfile.seek(0)
    macho.MachoFile.build_stream(m, outfile)
    outfile.close()

    print "moving foo to {0}".format(filename)
    os.rename("foo", filename)
