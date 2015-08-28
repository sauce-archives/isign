#
# Represents a file that can be signed.
# Executable, or dylib
#

from abc import ABCMeta
from codesig import (Codesig,
                     EntitlementsSlot,
                     ResourceDirSlot,
                     RequirementsSlot,
                     InfoSlot)
import logging
import macho
import os
import tempfile

log = logging.getLogger(__name__)


class Signable(object):
    __metaclass__ = ABCMeta

    slot_classes = []

    def __init__(self, app, path):
        log.debug("working on {0}".format(path))
        self.app = app
        self.path = path
        self.f = open(self.path, "rb")
        self.m = macho.MachoFile.parse_stream(self.f)

    def should_fill_slot(self, slot):
        return slot.__class__ in self.slot_classes

    def _sign_arch(self, arch_macho, arch_end, signer):
        cmds = {}
        for cmd in arch_macho.commands:
            name = cmd.cmd
            cmds[name] = cmd

        if 'LC_CODE_SIGNATURE' in cmds:
            lc_cmd = cmds['LC_CODE_SIGNATURE']
            # re-sign
            log.debug("re-signing")
            codesig_offset = arch_macho.macho_start + lc_cmd.data.dataoff
            self.f.seek(codesig_offset)
            codesig_data = self.f.read(lc_cmd.data.datasize)
            # log.debug(len(codesig_data))
        else:
            raise Exception("not implemented")
            # TODO: this doesn't actually work :(
            # see the makesig.py library, this was begun but not finished

        codesig = Codesig(self, codesig_data)
        codesig.resign(self.app, signer)

        # log.debug(new_codesig_cons)
        new_codesig_data = codesig.build_data()
        log.debug("old len: {0}".format(len(codesig_data)))
        log.debug("new len: {0}".format(len(new_codesig_data)))

        padding_length = len(codesig_data) - len(new_codesig_data)
        new_codesig_data += "\x00" * padding_length
        log.debug("padded len: {0}".format(len(new_codesig_data)))
        log.debug("----")
        # assert new_codesig_data != codesig_data

        lc_cmd = cmds['LC_CODE_SIGNATURE']
        lc_cmd.data.datasize = len(new_codesig_data)
        lc_cmd.bytes = macho.CodeSigRef.build(lc_cmd.data)

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
            log.debug(offset_fmt.format(write_offset,
                                        len(new_codesig_data),
                                        offset))
            temp.seek(write_offset)
            temp.write(new_codesig_data)

        # write new headers
        temp.seek(0)
        macho.MachoFile.build_stream(self.m, temp)
        temp.close()

        log.debug("moving temporary file to {0}".format(self.path))
        os.rename(temp.name, self.path)


class Executable(Signable):
    slot_classes = [EntitlementsSlot,
                    ResourceDirSlot,
                    RequirementsSlot,
                    InfoSlot]


class Dylib(Signable):
    slot_classes = [EntitlementsSlot,
                    RequirementsSlot,
                    InfoSlot]
