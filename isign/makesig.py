#
# Library to construct an LC_CODE_SIGNATURE construct
# from scratch. Does not work yet.
#
# Abandoned development May 2015 when it became clear that most
# apps that were uploaded to us would already be signed. But
# we may need this someday, so preserving here.
#

import construct
import hashlib
import logging
import math
import macho
import macho_cs
import utils


log = logging.getLogger(__name__)


def make_arg(data_type, arg):
    if data_type.name == 'Data':
        return construct.Container(data=arg,
                                   length=len(arg))
    elif data_type.name.lower() == 'expr':
        if isinstance(arg, construct.Container):
            # preserve expressions that are already containerized
            return arg
        return make_expr(*arg)
    elif data_type.name == 'slot':
        if arg == 'leafCert':
            return 0
        return arg
    elif data_type.name == 'Match':
        matchOp = arg[0]
        data = None
        if len(arg) > 1:
            data = construct.Container(data=arg[1],
                                       length=len(arg[1]))
        return construct.Container(matchOp=matchOp, Data=data)
    log.debug(data_type)
    log.debug(data_type.name)
    log.debug(arg)
    assert 0


def make_expr(op, *args):
    full_op = "op" + op
    data = None
    data_type = macho_cs.expr_args.get(full_op)
    if isinstance(data_type, macho_cs.Sequence):
        if len(data_type.subcons) == len(args):
            data = [make_arg(dt, arg) for dt, arg in zip(data_type.subcons, args)]
        else:
            # automatically nest binary operations to accept >2 args
            data = [make_arg(data_type.subcons[0], args[0]),
                    make_expr(op, *args[1:])]
    elif data_type:
        data = make_arg(data_type, args[0])
    return construct.Container(op=full_op,
                               data=data)


def make_requirements(drs, ident, common_name):
    expr = make_expr(
        'And',
        ('Ident', ident),
        ('AppleGenericAnchor',),
        ('CertField', 'leafCert', 'subject.CN', ['matchEqual', common_name]),
        ('CertGeneric', 1, '*\x86H\x86\xf7cd\x06\x02\x01', ['matchExists']))
    des_req = construct.Container(kind=1, expr=expr)
    des_req_data = macho_cs.Requirement.build(des_req)

    reqs = construct.Container(
        sb_start=0,
        count=1,
        BlobIndex=[construct.Container(type='kSecDesignatedRequirementType',
                                       offset=28,
                                       blob=construct.Container(magic='CSMAGIC_REQUIREMENT',
                                                                length=len(des_req_data) + 8,
                                                                data=des_req,
                                                                bytes=des_req_data))])

    if drs:
        dr_exprs = []
        for dr in drs.data.BlobIndex:
            if dr.blob is not None:
                dr_exprs.append(dr.blob.data.expr)
        # make_expr expects at least 2 arguments, need to verify that we pass those in, otherwise just return
        if len(dr_exprs) > 1:
            expr = make_expr('Or', *dr_exprs)
            lib_req = construct.Container(kind=1, expr=expr)
            lib_req_data = macho_cs.Requirement.build(lib_req)

            reqs.BlobIndex.append(construct.Container(type='kSecLibraryRequirementType',
                                                      offset=28 + len(des_req_data) + 8,
                                                      blob=construct.Container(magic='CSMAGIC_REQUIREMENT',
                                                                               length=len(lib_req_data) + 8,
                                                                               data=lib_req,
                                                                               bytes=lib_req_data)))
            reqs.count += 1

    return reqs


def make_basic_codesig(entitlements_file, drs, code_limit, hashes, signer, ident):
    common_name = signer.get_common_name()
    log.debug("ident: {}".format(ident))
    log.debug("codelimit: {}".format(code_limit))
    teamID = signer._get_team_id() + '\x00'
    empty_hash = "\x00" * 20
    cd = construct.Container(cd_start=None,
                             version=0x20200,
                             flags=0,
                             identOffset=52,
                             nSpecialSlots=5,
                             nCodeSlots=len(hashes),
                             codeLimit=code_limit,
                             hashSize=20,
                             hashType=1,
                             spare1=0,
                             pageSize=12,
                             spare2=0,
                             ident=ident + '\x00',
                             scatterOffset=0,
                             teamIDOffset=52 + len(ident) + 1,
                             teamID=teamID,
                             hashOffset=52 + (20 * 5) + len(ident) + 1 + len(teamID),
                             hashes=([empty_hash] * 5) + hashes,
                             )

    cd_data = macho_cs.CodeDirectory.build(cd)

    offset = 44
    cd_index = construct.Container(type=0,
                                   offset=offset,
                                   blob=construct.Container(magic='CSMAGIC_CODEDIRECTORY',
                                                            length=len(cd_data) + 8,
                                                            data=cd,
                                                            bytes=cd_data,
                                                            ))

    offset += cd_index.blob.length
    reqs_sblob = make_requirements(drs, ident, common_name)
    reqs_sblob_data = macho_cs.Entitlements.build(reqs_sblob)
    requirements_index = construct.Container(type=2,
                                             offset=offset,
                                             blob=construct.Container(magic='CSMAGIC_REQUIREMENTS',
                                                                      length=len(reqs_sblob_data) + 8,
                                                                      data="",
                                                                      bytes=reqs_sblob_data,
                                                                      ))
    offset += requirements_index.blob.length

    entitlements_index = None
    if entitlements_file != None:
        entitlements_bytes = open(entitlements_file, "rb").read()
        entitlements_index = construct.Container(type=5,
                                                 offset=offset,
                                                 blob=construct.Container(magic='CSMAGIC_ENTITLEMENT',
                                                                          length=len(entitlements_bytes) + 8,
                                                                          data="",
                                                                          bytes=entitlements_bytes
                                                                          ))
        offset += entitlements_index.blob.length

    sigwrapper_index = construct.Container(type=65536,
                                           offset=offset,
                                           blob=construct.Container(magic='CSMAGIC_BLOBWRAPPER',
                                                                    length=0 + 8,
                                                                    data="",
                                                                    bytes="",
                                                                    ))
    indicies = filter(None, [cd_index,
                requirements_index,
                entitlements_index,
                sigwrapper_index])

    superblob = construct.Container(
        sb_start=0,
        count=len(indicies),
        BlobIndex=indicies)
    data = macho_cs.SuperBlob.build(superblob)

    chunk = macho_cs.Blob.build(construct.Container(
        magic="CSMAGIC_EMBEDDED_SIGNATURE",
        length=len(data) + 8,
        data=data,
        bytes=data))
    return macho_cs.Blob.parse(chunk)


def make_signature(arch_macho, arch_offset, arch_size, cmds, f, entitlements_file, codesig_data_length, signer, ident):
    # NB: arch_offset is absolute in terms of file start.  Everything else is relative to arch_offset!

    # sign from scratch
    log.debug("signing from scratch")

    drs = None
    drs_lc = cmds.get('LC_DYLIB_CODE_SIGN_DRS')
    if drs_lc:
        drs = drs_lc.data.blob

    codesig_offset = utils.round_up(arch_size, 16)

    # generate code hashes
    log.debug("codesig offset: {}".format(codesig_offset))
    codeLimit = codesig_offset
    log.debug("new cL: {}".format(hex(codeLimit)))
    nCodeSlots = int(math.ceil(float(codesig_offset) / 0x1000))
    log.debug("new nCS: {}".format(nCodeSlots))


    # generate placeholder LC_CODE_SIGNATURE (like what codesign_allocate does)
    fake_hashes = ["\x00" * 20]*nCodeSlots

    codesig_cons = make_basic_codesig(entitlements_file,
            drs,
            codeLimit,
            fake_hashes,
            signer,
            ident)
    codesig_data = macho_cs.Blob.build(codesig_cons)

    cmd_data = construct.Container(dataoff=codesig_offset,
            datasize=codesig_data_length)
    cmd = construct.Container(cmd='LC_CODE_SIGNATURE',
            cmdsize=16,
            data=cmd_data,
            bytes=macho.CodeSigRef.build(cmd_data))

    log.debug("CS blob before: {}".format(utils.print_structure(codesig_cons, macho_cs.Blob)))
    log.debug("len(codesig_data): {}".format(len(codesig_data)))

    codesig_length = codesig_data_length
    log.debug("codesig length: {}".format(codesig_length))

    log.debug("old ncmds: {}".format(arch_macho.ncmds))
    arch_macho.ncmds += 1
    log.debug("new ncmds: {}".format(arch_macho.ncmds))

    log.debug("old sizeofcmds: {}".format(arch_macho.sizeofcmds))
    arch_macho.sizeofcmds += cmd.cmdsize
    log.debug("new sizeofcmds: {}".format(arch_macho.sizeofcmds))

    arch_macho.commands.append(cmd)

    hashes = []
    if codesig_data_length > 0:
        # Patch __LINKEDIT
        for lc in arch_macho.commands:
            if lc.cmd == 'LC_SEGMENT_64' or lc.cmd == 'LC_SEGMENT':
                if lc.data.segname == '__LINKEDIT':
                    log.debug("found __LINKEDIT, old filesize {}, vmsize {}".format(lc.data.filesize, lc.data.vmsize))

                    lc.data.filesize = utils.round_up(lc.data.filesize, 16) + codesig_length
                    if (lc.data.filesize > lc.data.vmsize):
                        lc.data.vmsize = utils.round_up(lc.data.filesize, 4096)

                    if lc.cmd == 'LC_SEGMENT_64':
                        lc.bytes = macho.Segment64.build(lc.data)
                    else:
                        lc.bytes = macho.Segment.build(lc.data)

                    log.debug("new filesize {}, vmsize {}".format(lc.data.filesize, lc.data.vmsize))


        actual_data = macho.MachO.build(arch_macho)
        log.debug("actual_data length with codesig LC {}".format(len(actual_data)))

        # Now seek to the start of the actual data and read until the end of the arch.
        f.seek(arch_offset + len(actual_data))
        bytes_to_read = codesig_offset + arch_offset - f.tell()
        file_slice = f.read(bytes_to_read)
        if len(file_slice) < bytes_to_read:
            log.warn("expected {} bytes but got {}, zero padding.".format(bytes_to_read, len(file_slice)))
            file_slice += ("\x00" * (bytes_to_read - len(file_slice)))
        actual_data += file_slice

        for i in xrange(nCodeSlots):
            actual_data_slice = actual_data[(0x1000 * i):(0x1000 * i + 0x1000)]

            actual = hashlib.sha1(actual_data_slice).digest()
            log.debug("Slot {} (File page @{}): {}".format(i, hex(0x1000 * i), actual.encode('hex')))
            hashes.append(actual)
    else:
        hashes = fake_hashes

    # Replace placeholder with real one.
    codesig_cons = make_basic_codesig(entitlements_file,
            drs,
            codeLimit,
            hashes,
            signer,
            ident)
    codesig_data = macho_cs.Blob.build(codesig_cons)
    cmd_data = construct.Container(dataoff=codesig_offset,
            datasize=len(codesig_data))
    cmd = construct.Container(cmd='LC_CODE_SIGNATURE',
            cmdsize=16,
            data=cmd_data,
            bytes=macho.CodeSigRef.build(cmd_data))
    arch_macho.commands[-1] = cmd
    cmds['LC_CODE_SIGNATURE'] = cmd
    return codesig_data
