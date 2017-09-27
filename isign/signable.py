#
# Represents a file that can be signed. A file that
# conforms to the Mach-O ABI.
#
# Executable, dylib, or framework.
#

from abc import ABCMeta
from .codesig import (Codesig,
                     EntitlementsSlot,
                     ResourceDirSlot,
                     RequirementsSlot,
                     ApplicationSlot,
                     InfoSlot)
import logging
from . import macho
from .makesig import make_signature
import os
import tempfile
from . import utils

log = logging.getLogger(__name__)


class Signable(object, metaclass=ABCMeta):
    slot_classes = []

    def __init__(self, bundle, path, signer):
        log.debug("working on {0}".format(path))
        self.bundle = bundle
        self.path = path
        self.signer = signer

        self.f = open(self.path, "rb")
        self.f.seek(0, os.SEEK_END)
        self.file_end = self.f.tell()
        self.f.seek(0)

        self.m = macho.MachoFile.parse_stream(self.f)
        self.sign_from_scratch = False

        # may set sign_from_scratch to True
        self.arches = self._parse_arches()


    def _parse_arches(self):
        """ parse architectures and associated Codesig """
        arch_macho = self.m.data
        arches = []
        if 'FatArch' in arch_macho:
            log.debug('found fat binary')
            for i, arch in enumerate(arch_macho.FatArch):
                log.debug('found fat slice: cputype {}, cpusubtype {}'.format(arch.cputype, arch.cpusubtype))
                this_arch_macho = arch.MachO
                log.debug('slice {}: arch offset: {}, size: {}'.format(i, arch.offset, arch.size))
                arch_object = self._get_arch(this_arch_macho,
                                             arch.offset,
                                             arch.size)
                arch_object['fat_index'] = i
                arches.append(arch_object)
        else:
            log.debug('found thin binary: cputype {}, cpusubtype {}'.format(arch_macho.cputype, arch_macho.cpusubtype))
            arches.append(self._get_arch(arch_macho,
                                         0,
                                         self.file_end))

        return arches

    def _get_arch(self, macho, arch_offset, arch_size):
        arch = {'macho': macho, 'arch_offset': arch_offset, 'arch_size': arch_size}

        arch['cmds'] = {}
        for cmd in macho.commands:
            name = cmd.cmd
            arch['cmds'][name] = cmd

        codesig_data = None

        if 'LC_CODE_SIGNATURE' in arch['cmds']:
            arch['lc_codesig'] = arch['cmds']['LC_CODE_SIGNATURE']
            codesig_offset = arch['macho'].macho_start + arch['lc_codesig'].data.dataoff
            self.f.seek(codesig_offset)
            codesig_data = self.f.read(arch['lc_codesig'].data.datasize)
            # log.debug("codesig len: {0}".format(len(codesig_data)))
        else:
            log.info("signing from scratch!")
            self.sign_from_scratch = True
            entitlements_file = self.bundle.get_entitlements_path()  #'/path/to/some/entitlements.plist'

            # Stage 1: Fake signature
            fake_codesig_data = make_signature(macho, arch_offset, arch_size, arch['cmds'], self.f, entitlements_file, 0, self.signer, self.bundle.get_info_prop('CFBundleIdentifier'))

            macho.ncmds -= 1
            macho.commands = macho.commands[:-1]

            # Get the length
            fake_codesig = Codesig(self, fake_codesig_data)
            fake_codesig.set_signature(self.signer)
            fake_codesig.update_offsets()
            fake_codesig_length = len(fake_codesig.build_data())

            log.debug("fake codesig length: {}".format(fake_codesig_length))

            # stage 2: real signature
            codesig_data = make_signature(macho, arch_offset, arch_size, arch['cmds'], self.f, entitlements_file, fake_codesig_length, self.signer, self.bundle.get_info_prop('CFBundleIdentifier'))


            arch['lc_codesig'] = arch['cmds']['LC_CODE_SIGNATURE']

        arch['codesig'] = Codesig(self, codesig_data)
        arch['codesig_len'] = len(codesig_data)

        if self.sign_from_scratch:
            arch['codesig_data'] = codesig_data

        return arch

    def _sign_arch(self, arch, app, signer):
    # Returns slice-relative offset, code signature blob
        arch['codesig'].resign(app, signer)

        new_codesig_data = arch['codesig'].build_data()
        new_codesig_len = len(new_codesig_data)
        log.debug("new codesig len is: {0}".format(new_codesig_len))

        padding_length = arch['codesig_len'] - new_codesig_len
        new_codesig_data += b"\x00" * padding_length
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

        if self.sign_from_scratch:
            return True

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

        temp = tempfile.NamedTemporaryFile('wb', delete=False)

        # If signing fat binary from scratch, need special handling

        # TODO: we assume that if any slice is unsigned, all slices are.  This should be true in practice but
        # we should still guard against this.
        if self.sign_from_scratch and 'FatArch' in self.m.data:
            assert len(self.arches) >= 2

            # todo(markwang): Update fat headers and mach_start for each slice if needewd
            log.debug('signing fat binary from scratch')

            sorted_archs = sorted(self.arches, key=lambda arch: arch['arch_offset'])


            prev_arch_end = 0
            for arch in sorted_archs:
                fatentry = arch['macho'] # has pointert to container

                codesig_arch_offset, new_codesig_data = self._sign_arch(arch, app, signer)
                codesig_file_offset = arch['arch_offset'] + codesig_arch_offset
                log.debug('existing arch slice: cputype {}, cpusubtype {}, offset {}, size {}'.format(fatentry.cputype, fatentry.cpusubtype, arch['arch_offset'], arch['arch_size']))
                log.debug("codesig arch offset: {2}, file offset: {0}, len: {1}".format(codesig_file_offset,
                                            len(new_codesig_data),
                                            codesig_arch_offset))
                assert codesig_file_offset >= (arch['arch_offset'] + arch['arch_size'])

                # Store the old slice offset/sizes because we need them when we copy the data slices from self.f to temp
                arch['old_arch_offset'] = arch['arch_offset']
                arch['old_arch_size'] = arch['arch_size']

                arch['codesig_arch_offset'] = codesig_arch_offset
                arch['codesig_data'] = new_codesig_data

                new_arch_size = codesig_arch_offset + len(new_codesig_data)

                if prev_arch_end > arch['arch_offset']:
                    arch['arch_offset'] = utils.round_up(prev_arch_end, 16384)

                prev_arch_end = arch['arch_offset'] + new_arch_size
                arch['arch_size'] = new_arch_size

                log.debug('new arch slice after codesig: offset {}, size {}'.format(arch['arch_offset'], arch['arch_size']))

            # write slices and code signatures in reverse order
            for arch in reversed(sorted_archs):
                self.f.seek(arch['old_arch_offset'])
                temp.seek(arch['arch_offset'])
                temp.write(self.f.read(arch['old_arch_size']))

                temp.seek(arch['arch_offset'] + arch['codesig_arch_offset'])
                temp.write(arch['codesig_data'])

                fatarch_info = self.m.data.FatArch[arch['fat_index']]
                fatarch_info.size = arch['arch_size']
                fatarch_info.offset = arch['arch_offset']



        else:
            # copy self.f into temp, reset to beginning of file
            self.f.seek(0)
            temp.write(self.f.read())
            temp.seek(0)

            # write new codesign blocks for each arch
            offset_fmt = ("offset: {2}, write offset: {0}, "
                          "new_codesig_data len: {1}")
            for arch in self.arches:
                offset, new_codesig_data = self._sign_arch(arch, app, signer)
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

        # make copy have same permissions
        mode = os.stat(self.path).st_mode
        os.chmod(temp.name, mode)
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
