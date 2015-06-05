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
import math
import macho
import macho_cs


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


def make_requirements(drs):
    expr = make_expr(
        'And',
        ('Ident', 'ca.michaelhan.NativeIOSTestApp'),
        ('AppleGenericAnchor',),
        # TODO pull this from the X509 cert
        # http://stackoverflow.com/questions/14565597/pyopenssl-reading-certificate-pkey-file
        ('CertField', 'leafCert', 'subject.CN', ['matchEqual', 'iPhone Developer: Steven Hazel (DU2T223MY8)']),
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
        dr_exprs = [dr.blob.data.expr for dr in drs.data.BlobIndex]
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


def make_basic_codesig(entitlements_file, drs, code_limit, hashes):
    ident = 'ca.michaelhan.NativeIOSTestApp' + '\x00'
    teamID = 'fake' + '\x00'
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
                             ident=ident,
                             scatterOffset=0,
                             teamIDOffset=52 + len(ident),
                             teamID=teamID,
                             hashOffset=52 + (20 * 5) + len(ident) + len(teamID),
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
    reqs_sblob = make_requirements(drs)
    reqs_sblob_data = macho_cs.Entitlements.build(reqs_sblob)
    requirements_index = construct.Container(type=2,
                                             offset=offset,
                                             blob=construct.Container(magic='CSMAGIC_REQUIREMENTS',
                                                                      length=len(reqs_sblob_data) + 8,
                                                                      data="",
                                                                      bytes=reqs_sblob_data,
                                                                      ))
    offset += requirements_index.blob.length

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
    indicies = [cd_index,
                requirements_index,
                entitlements_index,
                sigwrapper_index]

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


def make_signature(arch_macho, arch_end, cmds, f, entitlements_file):
    raise Exception("Making a signature is not fully implemented. This code was"
                    "abandoned since we think our customers will only give us signed"
                    "apps. But, it almost works, so it's preserved here.")
    # sign from scratch
    log.debug("signing from scratch")

    drs = None
    drs_lc = cmds.get('LC_DYLIB_CODE_SIGN_DRS')
    if drs_lc:
        drs = drs_lc.data.blob

    codesig_offset = arch_end

    # generate code hashes
    hashes = []
    #log.debug("codesig offset:", codesig_offset)
    start_offset = arch_macho.macho_start
    end_offset = macho_end
    #log.debug("new start-end", start_offset, end_offset)
    codeLimit = end_offset - start_offset
    #log.debug("new cL:", codeLimit)
    nCodeSlots = int(math.ceil(float(end_offset - start_offset) / 0x1000))
    #log.debug("new nCS:", nCodeSlots)
    for i in xrange(nCodeSlots):
        f.seek(start_offset + 0x1000 * i)
        actual_data = f.read(min(0x1000, end_offset - f.tell()))
        actual = hashlib.sha1(actual_data).digest()
        #log.debug(actual.encode('hex'))
        hashes.append(actual)

    codesig_cons = make_basic_codesig(entitlements_file,
            drs,
            codeLimit,
            hashes)
    codesig_data = macho_cs.Blob.build(codesig_cons)
    cmd_data = construct.Container(dataoff=codesig_offset,
            datasize=len(codesig_data))
    cmd = construct.Container(cmd='LC_CODE_SIGNATURE',
            cmdsize=16,
            data=cmd_data,
            bytes=macho.CodeSigRef.build(cmd_data))
    arch_macho.commands.append(cmd)
    arch_macho.ncmds += 1
    arch_macho.sizeofcmds += len(macho.LoadCommand.build(cmd))
    cmds['LC_CODE_SIGNATURE'] = cmd

