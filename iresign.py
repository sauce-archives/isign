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


def sign(data):
    proc = subprocess.Popen("%s cms"
                            " -sign -binary -nosmimecap"
                            " -certfile %s"
                            " -signer %s"
                            " -inkey %s"
                            " -keyform pkcs12 "
                            " -outform DER" %
                            (OPENSSL,
                             '~/applecerts.pem',
                             '~/devcert.pem',
                             '~/devkey.p12'),
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


def main():
    parser = OptionParser()
    options, args = parser.parse_args()
    filename = args[0]

    m = macholib.MachO.MachO(filename)
    for cmd in m.headers[0].commands:
        try:
            print cmd[0].get_cmd_name(), cmd[1].dataoff, cmd[1].datasize
            if cmd[0].get_cmd_name() == "LC_DYLIB_CODE_SIGN_DRS":
                f = open(filename, "rb")
                codesigdrs_offset = cmd[1].dataoff
                if m.fat:
                    codesigdrs_offset += 0x1000
                f.seek(codesigdrs_offset)
                codesigdrs_data = f.read(cmd[1].datasize)
                print len(codesigdrs_data)
                print hexdump(codesigdrs_data)
                print macho_cs.Blob.parse(codesigdrs_data)
        except:
            print cmd[0].get_cmd_name()
    codesig_cmd = m.headers[0].commands[-1]
    assert codesig_cmd[0].get_cmd_name() == "LC_CODE_SIGNATURE"
    f = open(filename, "rb")
    #f.seek(0, os.SEEK_END)
    #print f.tell()
    codesig_offset = codesig_cmd[1].dataoff
    if m.fat:
        codesig_offset += 0x1000
    f.seek(codesig_offset)
    codesig_data = f.read(codesig_cmd[1].datasize)
    #print len(codesig_data)
    #print hexdump(codesig_data)

    codesig_cons = macho_cs.Blob.parse(codesig_data)

    def do_blob(sblob):
        print sblob

        print "entitlements:"
        entitlements = sblob.data.BlobIndex[2].blob
        entitlements_data = macho_cs.Blob_.build(entitlements)
        print hashlib.sha1(entitlements_data).hexdigest()
        entitlements.bytes = open("Entitlements.plist", "rb").read()
        entitlements.length = len(entitlements.bytes) + 8
        entitlements_data = macho_cs.Blob_.build(entitlements)
        print hashlib.sha1(entitlements_data).hexdigest()

        print "requirements:"
        requirements = sblob.data.BlobIndex[1].blob
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

        print "certs:"
        for blob in sblob.data.BlobIndex:
            if blob.blob.magic == 'CSMAGIC_BLOBWRAPPER':
                #print_parsed_asn1(blob.blob.data.data.value)
                #open("sigrip.der", "wb").write(blob.blob.data.data.value)
                cd = sblob.data.BlobIndex[0].blob
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

                sig = sign(cd_data)
                oldsig = blob.blob.bytes.value
                print "sig len:", len(sig)
                print "old sig len:", len(oldsig)
                #open("my_sigrip.der", "wb").write(sig)
                #print hexdump(oldsig)
                blob.blob.data = construct.Container(data=sig)
                #print_parsed_asn1(sig)
                #blob.blob.data = construct.Container(data="hahaha")
                blob.blob.length = len(blob.blob.data.data) + 8
                blob.blob.bytes = blob.blob.data.data
                print len(blob.blob.bytes)
                #print hexdump(blob.blob.bytes)
                break
        superblob = macho_cs.SuperBlob.build(sblob.data)
        sblob.length = len(superblob) + 8
        sblob.bytes = superblob

        # print hashes
        cd = sblob.data.BlobIndex[0].blob.data
        end_offset = cd.codeLimit
        if m.fat:
            end_offset += 0x1000
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
        return macho_cs.Blob.build(sblob)

    new_codesig_data = do_blob(codesig_cons)
    print "old len:", len(codesig_data)
    print "new len:", len(new_codesig_data)

    new_codesig_data += "\x00" * (len(codesig_data) - len(new_codesig_data))
    print "padded len:", len(new_codesig_data)
    print "----"
    #print hexdump(new_codesig_data)
    #assert new_codesig_data != codesig_data

    codesig_cmd[1].datasize = len(new_codesig_data)
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
    f3.write(f.read(codesig_cmd[1].dataoff - f3.tell()))
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
