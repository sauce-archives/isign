import construct
import distutils
import hashlib
import isign
import subprocess
import os
import OpenSSL
from optparse import OptionParser
# from hexdump import hexdump

import macho
import macho_cs


OPENSSL = os.getenv('OPENSSL', distutils.spawn.find_executable('openssl'))


def sign(data, signer_cert_file, signer_key_file, cert_file):
    proc = subprocess.Popen("%s cms"
                            " -sign -binary -nosmimecap"
                            " -certfile %s"
                            " -signer %s"
                            " -inkey %s"
                            " -keyform pkcs12 "
                            " -outform DER" %
                            (OPENSSL,
                             cert_file,
                             signer_cert_file,
                             signer_key_file),
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            shell=True)
    proc.stdin.write(data)
    out, err = proc.communicate()
    print err
    return out


def print_parsed_asn1(data):
    proc = subprocess.Popen('openssl asn1parse -inform DER -i',
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            shell=True)
    proc.stdin.write(data)
    out, err = proc.communicate()
    print out


def get_codesig_blob(codesig_cons, magic):
    for index in codesig_cons.data.BlobIndex:
        if index.blob.magic == magic:
            return index.blob
    raise KeyError(magic)


def make_entitlements_data(codesig_cons, entitlements_file):
    print "entitlements:"
    entitlements_data = None
    try:
        entitlements = get_codesig_blob(codesig_cons, 'CSMAGIC_ENTITLEMENT')
    except KeyError:
        print "no entitlements found"
    else:
        # make entitlements data if slot was found
        entitlements_data = macho_cs.Blob_.build(entitlements)
        print hashlib.sha1(entitlements_data).hexdigest()

        entitlements.bytes = open(entitlements_file, "rb").read()
        entitlements.length = len(entitlements.bytes) + 8
        entitlements_data = macho_cs.Blob_.build(entitlements)
        print hashlib.sha1(entitlements_data).hexdigest()
    print
    return entitlements_data


def make_requirements_data(codesig_cons, signer_key_file):
    print "requirements:"
    requirements = get_codesig_blob(codesig_cons, 'CSMAGIC_REQUIREMENTS')
    requirements_data = macho_cs.Blob_.build(requirements)
    print hashlib.sha1(requirements_data).hexdigest()
    signer_key_data = open(os.path.expanduser(signer_key_file), "rb").read()
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
    return requirements_data


# TODO we are deferring what to do with the seal file way too late here
def make_codedirectory_data(codesig_cons,
                            entitlements_data,
                            requirements_data,
                            seal_file,
                            team_id):
    print "code directory:"
    cd = get_codesig_blob(codesig_cons, 'CSMAGIC_CODEDIRECTORY')
    # print cd
    hashnum = 0
    # if this is an app, add the entitlements and seal hash
    if cd.data.nSpecialSlots == 5:
        assert entitlements_data is not None
        cd.data.hashes[hashnum] = hashlib.sha1(entitlements_data).digest()
        hashnum += 2
        seal_data = open(seal_file, "rb").read()
        cd.data.hashes[hashnum] = hashlib.sha1(seal_data).digest()
        hashnum += 1
    else:
        # this is a library, should have 2 special slots
        assert cd.data.nSpecialSlots == 2
    cd.data.hashes[hashnum] = hashlib.sha1(requirements_data).digest()
    cd.data.teamID = team_id
    cd.bytes = macho_cs.CodeDirectory.build(cd.data)
    cd_data = macho_cs.Blob_.build(cd)
    print len(cd_data)
    # open("cdrip", "wb").write(cd_data)
    print "CDHash:", hashlib.sha1(cd_data).hexdigest()
    print
    return cd_data


def rewrite_signature(codesig_cons,
                      cd_data,
                      signer_cert_file,
                      signer_key_file,
                      cert_file):
    print "sig:"
    sigwrapper = get_codesig_blob(codesig_cons, 'CSMAGIC_BLOBWRAPPER')
    # print_parsed_asn1(sigwrapper.data.data.value)
    # open("sigrip.der", "wb").write(sigwrapper.data.data.value)
    sig = sign(cd_data,
               signer_cert_file,
               signer_key_file,
               cert_file)
    oldsig = sigwrapper.bytes.value
    print "sig len:", len(sig)
    print "old sig len:", len(oldsig)
    # open("my_sigrip.der", "wb").write(sig)
    # print hexdump(oldsig)
    sigwrapper.data = construct.Container(data=sig)
    # print_parsed_asn1(sig)
    # sigwrapper.data = construct.Container(data="hahaha")
    sigwrapper.length = len(sigwrapper.data.data) + 8
    sigwrapper.bytes = sigwrapper.data.data
    # print len(sigwrapper.bytes)
    # print hexdump(sigwrapper.bytes)
    print


def update_offsets(codesig_cons):
    # update section offsets, to account for any length changes
    offset = codesig_cons.data.BlobIndex[0].offset
    for blob in codesig_cons.data.BlobIndex:
        blob.offset = offset
        offset += len(macho_cs.Blob.build(blob.blob))

    superblob = macho_cs.SuperBlob.build(codesig_cons.data)
    codesig_cons.length = len(superblob) + 8
    codesig_cons.bytes = superblob


def resign_cons(codesig_cons,
                entitlements_file,
                seal_file,
                signer_cert_file,
                signer_key_file,
                cert_file):

    # TODO obtain this from entitlements_file
    team_id = "JWKXD469L2"

    # TODO it's probably not necessary to pass the *_data around
    # since it can be re-obtained from the cons
    entitlements_data = make_entitlements_data(codesig_cons, entitlements_file)
    requirements_data = make_requirements_data(codesig_cons, signer_key_file)
    cd_data = make_codedirectory_data(codesig_cons,
                                      entitlements_data,
                                      requirements_data,
                                      seal_file,
                                      team_id)
    rewrite_signature(codesig_cons,
                      cd_data,
                      signer_cert_file,
                      signer_key_file,
                      cert_file)
    update_offsets(codesig_cons)
    return codesig_cons


def sign_architecture(arch_macho, arch_end, f, entitlements_file, seal_file):
    cmds = {}
    for cmd in arch_macho.commands:
        name = cmd.cmd
        cmds[name] = cmd

    lc_cmd = cmds['LC_CODE_SIGNATURE']

    if 'LC_CODE_SIGNATURE' in cmds:
        # re-sign
        print "re-signing"
        codesig_offset = arch_macho.macho_start + lc_cmd.data.dataoff
        f.seek(codesig_offset)
        codesig_data = f.read(lc_cmd.data.datasize)
        # print len(codesig_data)
        # print hexdump(codesig_data)
        codesig_cons = macho_cs.Blob.parse(codesig_data)
    else:
        isign.make_signature(arch_macho, arch_end, cmds, f, entitlements_file)

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

    new_codesig_cons = resign_cons(codesig_cons,
                                   entitlements_file,
                                   seal_file,
                                   '~/devcert.pem',
                                   '~/devkey.p12',
                                   '~/applecerts.pem')
    # print new_codesig_cons
    new_codesig_data = macho_cs.Blob.build(new_codesig_cons)
    print "old len:", len(codesig_data)
    print "new len:", len(new_codesig_data)

    new_codesig_data += "\x00" * (len(codesig_data) - len(new_codesig_data))
    print "padded len:", len(new_codesig_data)
    print "----"
    # print hexdump(new_codesig_data)
    # assert new_codesig_data != codesig_data

    lc_cmd.data.datasize = len(new_codesig_data)
    lc_cmd.bytes = macho.CodeSigRef.build(cmd.data)

    offset = lc_cmd.data.dataoff
    return offset, new_codesig_data


def sign_file(filename, entitlements_file):
    print "working on {0}".format(filename)
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
                                                     seal_file)
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


def main():
    parser = OptionParser()
    options, args = parser.parse_args()
    filename = args[0]
    entitlements_file = "Entitlements.plist"
    sign_file(filename, entitlements_file)


if __name__ == '__main__':
    main()
