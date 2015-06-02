CodeDirectory slots
===================

A signature is mostly composed of hashes of blocks of the file's
contents. However, at some point, Apple added special hashes so the
state of other resources in the app could be captured in the signature.
For instance, the Info.plist gets its own hash, and ultimately the
hashes of all the other files are also captured in the ResourceDirectory
hash. Together, all these special hashes are called the CodeDirectory.

Perhaps to indicate that these are special hashes, they were given
negative offsets in the list of hashes.

For instance, if you do ``codesign -d -r- --verbose=20 some.app``

::

    Executable=...
    Identifier=com.somecompany.someapp
    Format=bundle with Mach-O universal (armv7 arm64)
    CodeDirectory v=20200 size=874 flags=0x0(none) hashes=35+5 location=embedded
    Hash type=sha1 size=20
        -5=0ea763a5bc4d19b0e03315a956deecd97693a661
        -4=0000000000000000000000000000000000000000
        -3=b353e6ce8464fd8ae32cfcf09e7c9015b7378054
        -2=32a5edb9b03a0bea2d7bc30cfdddadab7dab841c
        -1=46ebe92997b23b2e2187a21714c8cc32c347bf35
         0=70e024fdab3426c375cf283d384de58ec6fff438
         1=1ceaf73df40e531df3bfb26b4fb7cd95fb7bff1d
         2=1ceaf73df40e531df3bfb26b4fb7cd95fb7bff1d
         ...

The CodeDirectory hashes have stable negative indices - for instance, -1
is always the hash of the Info.plist file. The indices for the
CodeDirectory hashes are sometimes called slots.

When building the CodeDirectory, We need to observe these constraints:

-  Executables should have all 5 slots in their codedirectory

-  Dylibs only need 2 slots, but sometimes have been compiled with 5

-  Dylibs should never include the ResourceDir slot, even if they have 5
   slots

-  We should delay calculating hashes until we know we are going to use
   them

-  Nobody uses the Application-specific slot anyway

-  At least so far, we don't need to change the Info.plist slot when
   re-signing
