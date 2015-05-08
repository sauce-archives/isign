import construct
import distutils
import hashlib
import subprocess
import macholib.mach_o
import macholib.MachO
from optparse import OptionParser
import os
from hexdump import hexdump

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
    for blob in codesig_cons.data.BlobIndex:
        if blob.blob.magic == magic:
            return blob.blob
    raise KeyError(magic)


def resign_cons(codesig_cons, signer_cert_file, signer_key_file, cert_file):
    print "entitlements:"
    entitlements = get_codesig_blob(codesig_cons, 'CSMAGIC_ENTITLEMENT')
    entitlements_data = macho_cs.Blob_.build(entitlements)
    print hashlib.sha1(entitlements_data).hexdigest()
    entitlements.bytes = open("Entitlements.plist", "rb").read()
    entitlements.length = len(entitlements.bytes) + 8
    entitlements_data = macho_cs.Blob_.build(entitlements)
    print hashlib.sha1(entitlements_data).hexdigest()
    print

    print "requirements:"
    requirements = get_codesig_blob(codesig_cons, 'CSMAGIC_REQUIREMENTS')
    #print hexdump(requirements.bytes.value)
    print hashlib.sha1(requirements.bytes.value).hexdigest()
    cn = requirements.data.BlobIndex[0].blob.data.expr.data[1].data[1].data[0].data[2].Data
    cn.data = 'iPhone Developer: Steven Hazel (DU2T223MY8)'
    cn.length = len(cn.data)
    requirements.data.BlobIndex[0].blob.bytes = macho_cs.Requirement.build(requirements.data.BlobIndex[0].blob.data)
    requirements.data.BlobIndex[0].blob.length = len(requirements.data.BlobIndex[0].blob.bytes) + 8
    requirements.bytes = macho_cs.Entitlements.build(requirements.data)
    requirements.length = len(requirements.bytes) + 8
    requirements_data = macho_cs.Blob_.build(requirements)
    print hashlib.sha1(requirements_data).hexdigest()
    #print hexdump(requirements_data)
    print

    print "code directory:"
    cd = get_codesig_blob(codesig_cons, 'CSMAGIC_CODEDIRECTORY')
    print cd
    cd.data.hashes[0] = hashlib.sha1(entitlements_data).digest()
    cd.data.hashes[2] = hashlib.sha1(open("../resigned/NativeIOSTestApp.app/_CodeSignature/CodeResources", "rb").read()).digest()
    cd.data.hashes[3] = hashlib.sha1(requirements_data).digest()
    cd.data.teamID = "JWKXD469L2"
    cd.bytes = macho_cs.CodeDirectory.build(cd.data)
    cd_data = macho_cs.Blob_.build(cd)
    print len(cd_data)
    #open("cdrip", "wb").write(cd_data)
    print "CDHash:", hashlib.sha1(cd_data).hexdigest()
    print

    print "sig:"
    sigwrapper = get_codesig_blob(codesig_cons, 'CSMAGIC_BLOBWRAPPER')
    #print_parsed_asn1(sigwrapper.data.data.value)
    #open("sigrip.der", "wb").write(sigwrapper.data.data.value)
    sig = sign(cd_data,
               signer_cert_file,
               signer_key_file,
               cert_file)
    oldsig = sigwrapper.bytes.value
    print "sig len:", len(sig)
    print "old sig len:", len(oldsig)
    #open("my_sigrip.der", "wb").write(sig)
    #print hexdump(oldsig)
    sigwrapper.data = construct.Container(data=sig)
    #print_parsed_asn1(sig)
    #sigwrapper.data = construct.Container(data="hahaha")
    sigwrapper.length = len(sigwrapper.data.data) + 8
    sigwrapper.bytes = sigwrapper.data.data
    print len(sigwrapper.bytes)
    #print hexdump(sigwrapper.bytes)
    print

    superblob = macho_cs.SuperBlob.build(codesig_cons.data)
    codesig_cons.length = len(superblob) + 8
    codesig_cons.bytes = superblob

    return codesig_cons


def main():
    parser = OptionParser()
    options, args = parser.parse_args()
    filename = args[0]

    m = macholib.MachO.MachO(filename)
    base_offset = 0
    if m.fat:
        base_offset = 0x1000

    cmds = {}
    for cmd in m.headers[0].commands:
        name = cmd[0].get_cmd_name()
        if isinstance(cmd[1], macholib.mach_o.linkedit_data_command):
            print name, cmd[1].dataoff, cmd[1].datasize
            cmds[name] = cmd[1]

    f = open(filename, "rb")
    codesigdrs_offset = base_offset + cmds['LC_DYLIB_CODE_SIGN_DRS'].dataoff
    f.seek(codesigdrs_offset)
    codesigdrs_data = f.read(cmds['LC_DYLIB_CODE_SIGN_DRS'].datasize)
    print len(codesigdrs_data)
    print hexdump(codesigdrs_data)
    print macho_cs.Blob.parse(codesigdrs_data)

    f = open(filename, "rb")
    codesig_offset = base_offset + cmds['LC_CODE_SIGNATURE'].dataoff
    f.seek(codesig_offset)
    codesig_data = f.read(cmds['LC_CODE_SIGNATURE'].datasize)
    #print len(codesig_data)
    #print hexdump(codesig_data)

    codesig_cons = macho_cs.Blob.parse(codesig_data)
    print codesig_cons

    # print hashes
    cd = codesig_cons.data.BlobIndex[0].blob.data
    end_offset = base_offset + cd.codeLimit
    start_offset = ((end_offset + 0xfff) & ~0xfff) - (cd.nCodeSlots * 0x1000)
    for i in xrange(cd.nSpecialSlots):
        expected = cd.hashes[i]
        print "special exp=%s" % expected.encode('hex')
    for i in xrange(cd.nCodeSlots):
        expected = cd.hashes[cd.nSpecialSlots + i]
        f.seek(start_offset + 0x1000 * i)
        actual_data = f.read(min(0x1000, end_offset - f.tell()))
        actual = hashlib.sha1(actual_data).digest()
        print '[%s] exp=%s act=%s' % (
            ('bad', 'ok ')[expected == actual],
            expected.encode('hex'),
            actual.encode('hex')
        )

    new_codesig_cons = resign_cons(codesig_cons,
                                   '~/devcert.pem',
                                   '~/devkey.p12',
                                   '~/applecerts.pem')
    new_codesig_data = macho_cs.Blob.build(new_codesig_cons)
    print "old len:", len(codesig_data)
    print "new len:", len(new_codesig_data)

    new_codesig_data += "\x00" * (len(codesig_data) - len(new_codesig_data))
    print "padded len:", len(new_codesig_data)
    print "----"
    #print hexdump(new_codesig_data)
    #assert new_codesig_data != codesig_data

    cmds['LC_CODE_SIGNATURE'].datasize = len(new_codesig_data)
    for cmd in m.headers[0].commands:
        load_cmd, data, _ = cmd
        fileend = 0
        if isinstance(data, macholib.mach_o.linkedit_data_command):
            fileend = max(fileend, data.dataoff + data.datasize)

    for cmd in m.headers[0].commands:
        load_cmd, data, _ = cmd
        if isinstance(data, macholib.mach_o.segment_command):
            print repr(data.segname)
            if data.segname.startswith("__LINKEDIT"):
                filesize = fileend - data.fileoff
                print "setting filesize to", filesize
                data.filesize = filesize

    f3 = open("foo", "wb")
    m.write(f3)
    print "wrote mach-o header of length:", f3.tell()
    f.seek(f3.tell())  # FIXME -- really want original f header size, not new m length
    f3.write(f.read(cmds['LC_CODE_SIGNATURE'].dataoff - f3.tell()))
    for cmd in m.headers[0].commands:
        load_cmd, data, _ = cmd
        filesize = 0
        if isinstance(data, macholib.mach_o.linkedit_data_command):
            if load_cmd.get_cmd_name() == "LC_CODE_SIGNATURE":
                print "writing codesig"
                f3.seek(data.dataoff)
                f3.write(new_codesig_data)
            else:
                # FIXME this is a no-op
                f.seek(data.dataoff)
                f3.seek(data.dataoff)
                f3.write(f.read(data.datasize))
            filesize = max(filesize, data.dataoff + data.datasize)
    f3.close()


if __name__ == '__main__':
    main()
