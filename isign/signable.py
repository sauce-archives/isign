#
# Represents a file that can be signed. A file that
# conforms to the Mach-O ABI.
#
# Executable, dylib, or framework.
#

from abc import ABCMeta
from codesig import (Codesig,
                     EntitlementsSlot,
                     ResourceDirSlot,
                     RequirementsSlot,
                     ApplicationSlot,
                     InfoSlot)
import logging
import macho
from makesig import make_signature
import os
import tempfile

log = logging.getLogger(__name__)

class Signable(object):
    __metaclass__ = ABCMeta

    slot_classes = []

    def __init__(self, bundle, path):
        log.debug("working on {0}".format(path))
        self.bundle = bundle
        self.path = path

        self.f = open(self.path, "rb")
        self.f.seek(0, os.SEEK_END)
        self.file_end = self.f.tell()
        self.f.seek(0)

        self.m = macho.MachoFile.parse_stream(self.f)
        self.arches = self._parse_arches()

    def _parse_arches(self):
        """ parse architectures and associated Codesig """
        arch_macho = self.m.data
        arches = []
        if 'FatArch' in arch_macho:
            for i, arch in enumerate(arch_macho.FatArch):
                this_arch_macho = arch.MachO
                next_macho = i + 1
                if next_macho == len(arch_macho.FatArch):  # last
                    this_macho_end = self.file_end
                else:
                    next_arch = arch_macho.FatArch[next_macho]
                    this_macho_end = next_arch.MachO.macho_start
                arches.append(self._get_arch(this_arch_macho,
                                             this_macho_end))
        else:
            arches.append(self._get_arch(arch_macho,
                                         self.file_end))

        return arches

    def _get_arch(self, macho, macho_end):
        arch = {'macho': macho, 'macho_end': macho_end}

        arch['cmds'] = {}
        for cmd in macho.commands:
            name = cmd.cmd
            arch['cmds'][name] = cmd

        if 'LC_CODE_SIGNATURE' in arch['cmds']:
            arch['lc_codesig'] = arch['cmds']['LC_CODE_SIGNATURE']
            codesig_offset = arch['macho'].macho_start + arch['lc_codesig'].data.dataoff
            self.f.seek(codesig_offset)
            codesig_data = self.f.read(arch['lc_codesig'].data.datasize)
            # log.debug("codesig len: {0}".format(len(codesig_data)))
        else:
            log.info("signing from scratch!")
            entitlements_file = '/Users/neilk/projects/ios-apps/unsigned_entitlements.plist'
            codesig_data = make_signature(macho, macho_end, arch['cmds'], self.f, entitlements_file)
            arch['lc_codesig'] = arch['cmds']['LC_CODE_SIGNATURE']

        arch['codesig'] = Codesig(self, codesig_data)
        arch['codesig_len'] = len(codesig_data)

        return arch

    def _sign_arch(self, arch, app, signer):

        arch['codesig'].resign(app, signer)

        new_codesig_data = arch['codesig'].build_data()
        new_codesig_len = len(new_codesig_data)
        # log.debug("new codesig len: {0}".format(new_codesig_len))

        padding_length = arch['codesig_len'] - new_codesig_len
        new_codesig_data += "\x00" * padding_length
        # log.debug("padded len: {0}".format(len(new_codesig_data)))
        # log.debug("----")

        cmd = arch['lc_codesig']
        cmd.data.datasize = len(new_codesig_data)
        cmd.bytes = macho.CodeSigRef.build(arch['lc_codesig'].data)

        offset = cmd.data.dataoff
        return offset, new_codesig_data

    def should_fill_slot(self, codesig, slot):
        slot_class = slot.__class__
        if slot_class not in self.slot_classes:
            # This signable does not have this slot
            return False

        if slot_class == InfoSlot and not self.bundle.info_props_changed():
            # No Info.plist changes, don't fill
            return False

        if slot_class == ApplicationSlot and not codesig.is_sha256_signature():
            # Application slot only needs to be zeroed out when there's a sha256 layer
            return False

        return True

    def get_changed_bundle_id(self):
        # Return a bundle ID to assign if Info.plist's CFBundleIdentifier value was changed
        if self.bundle.info_prop_changed('CFBundleIdentifier'):
            return self.bundle.get_info_prop('CFBundleIdentifier')
        else:
            return None

    def sign(self, app, signer):
        # copy self.f into temp, reset to beginning of file
        temp = tempfile.NamedTemporaryFile('wb', delete=False)
        self.f.seek(0)
        temp.write(self.f.read())
        temp.seek(0)

        # write new codesign blocks for each arch
        # offset_fmt = ("offset: {2}, write offset: {0}, "
        #               "new_codesig_data len: {1}")
        for arch in self.arches:
            offset, new_codesig_data = self._sign_arch(arch, app, signer)
            write_offset = arch['macho'].macho_start + offset
            # log.debug(offset_fmt.format(write_offset,
            #                             len(new_codesig_data),
            #                             offset))
            temp.seek(write_offset)
            temp.write(new_codesig_data)

        # write new headers
        temp.seek(0)
        macho.MachoFile.build_stream(self.m, temp)
        temp.close()

        # log.debug("moving temporary file to {0}".format(self.path))
        os.rename(temp.name, self.path)


class Executable(Signable):
    """ The main executable of an app. """
    slot_classes = [EntitlementsSlot,
                    ResourceDirSlot,
                    RequirementsSlot,
                    ApplicationSlot,
                    InfoSlot]

class Dylib(Signable):
    """ A dynamic library that isn't part of its own bundle, e.g.
        the Swift libraries.

        TODO: Dylibs have an info slot, however the Info.plist is embedded in the __TEXT section
              of the file (__info_plist) instead of being a seperate file.
              Add read/write of the embedded Info.plist so we can include InfoSlot below.
    """
    slot_classes = [EntitlementsSlot,
                    RequirementsSlot]

class Appex(Signable):
    """ An app extension  """
    slot_classes = [EntitlementsSlot,
                    RequirementsSlot,
                    InfoSlot]


class Framework(Signable):
    """ The main executable of a Framework, which is a library of sorts
        but is bundled with both files and code """
    slot_classes = [ResourceDirSlot,
                    RequirementsSlot,
                    InfoSlot]
