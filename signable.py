#
# Represents a file that can be signed.
# Executable, or dylib
#

from abc import ABCMeta
from codesig import Codesig
import macho
import os
import tempfile


class Signable(object):
    __metaclass__ = ABCMeta

    def __init__(self, app, path):
        print "working on {0}".format(path)
        self.app = app
        self.path = path
        self.f = open(self.path, "rb")
        self.m = macho.MachoFile.parse_stream(self.f)

    def _sign_arch(self, arch_macho, arch_end, signer):
        cmds = {}
        for cmd in arch_macho.commands:
            name = cmd.cmd
            cmds[name] = cmd

        if 'LC_CODE_SIGNATURE' in cmds:
            lc_cmd = cmds['LC_CODE_SIGNATURE']
            # re-sign
            print "re-signing"
            codesig_offset = arch_macho.macho_start + lc_cmd.data.dataoff
            self.f.seek(codesig_offset)
            codesig_data = self.f.read(lc_cmd.data.datasize)
            # print len(codesig_data)
            # print hexdump(codesig_data)
        else:
            raise Exception("not implemented")
            # TODO: this doesn't actually work :(
            # see the makesig.py library, this was begun but not finished

        codesig = Codesig(self, codesig_data)
        codesig.resign(self.app, signer)

        # print new_codesig_cons
        new_codesig_data = codesig.build_data()
        print "old len:", len(codesig_data)
        print "new len:", len(new_codesig_data)

        padding_length = len(codesig_data) - len(new_codesig_data)
        new_codesig_data += "\x00" * padding_length
        print "padded len:", len(new_codesig_data)
        print "----"
        # print hexdump(new_codesig_data)
        # assert new_codesig_data != codesig_data

        lc_cmd = cmds['LC_CODE_SIGNATURE']
        lc_cmd.data.datasize = len(new_codesig_data)
        lc_cmd.bytes = macho.CodeSigRef.build(cmd.data)

        offset = lc_cmd.data.dataoff
        return offset, new_codesig_data

    def sign(self, signer):
        arch_macho = self.m.data
        self.f.seek(0, os.SEEK_END)
        file_end = self.f.tell()
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

        # copy self.f into temp, reset to beginning of file
        temp = tempfile.NamedTemporaryFile('wb', delete=False)
        self.f.seek(0)
        temp.write(self.f.read())
        temp.seek(0)

        # write new codesign blocks for each arch
        offset_fmt = ("offset: {2}, write offset: {0}, "
                      "new_codesig_data len: {1}")
        for arch in arches:
            offset, new_codesig_data = self._sign_arch(arch['macho'],
                                                       arch['macho_end'],
                                                       signer)
            write_offset = arch['macho'].macho_start + offset
            print offset_fmt.format(write_offset,
                                    len(new_codesig_data),
                                    offset)
            temp.seek(write_offset)
            temp.write(new_codesig_data)

        # write new headers
        temp.seek(0)
        macho.MachoFile.build_stream(self.m, temp)
        temp.close()

        print "moving temporary file to {0}".format(self.path)
        os.rename(temp.name, self.path)


class Executable(Signable):
    nSpecialSlots = 5
    cdEntitlementSlot = -5
    cdApplicationSlot = -4
    cdResourceDirSlot = -3
    cdRequirementsSlot = -2
    cdInfoSlot = -1


class Dylib(Signable):
    """ In a .app, the dylib seems to have 2 special slots """
    nSpecialSlots = 2
    cdRequirementsSlot = -2
    cdInfoSlot = -1


class IpaDylib(Signable):
    """ when (re)building an IPA, we seem to need five
        slots like an executable. Except, in the normal way
        of code signing, dylibs are signed before the seal
        is created, so we make sure to leave this blank.  """
    nSpecialSlots = 5
    cdEntitlementSlot = -5
    cdApplicationSlot = -4
    # does not have cdResourceDirSlot; always blank
    cdRequirementsSlot = -2
    cdInfoSlot = -1
