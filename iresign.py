import biplist
from codesig import Codesig
import isign
import macho
import os
import tempfile
# from hexdump import hexdump



# in Entitlement plists
TEAM_IDENTIFIER_KEY = 'com.apple.developer.team-identifier'


def get_team_id(entitlements_file):
    # TODO obtain this from entitlements
    entitlements_plist = biplist.readPlist(entitlements_file)
    return entitlements_plist[TEAM_IDENTIFIER_KEY]


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
    else:
        # TODO: this doesn't actually work :(
        isign.make_signature(arch_macho, arch_end, cmds, f, entitlements_file)
        # TODO get the data from construct back from this method as codesig_data...

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

    codesig = Codesig(codesig_data)
    codesig.resign(entitlements_file,
                   seal_file,
                   signer,
                   team_id)

    # print new_codesig_cons
    new_codesig_data = codesig.build_data()
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
    outfile = tempfile.NamedTemporaryFile('wb', delete=False)
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

    print "moving temporary file to {0}".format(filename)
    os.rename(outfile.name, filename)
