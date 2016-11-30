The test credentials in this directory cannot be used to sign apps for use on any iOS device. They
are sufficiently similar to a real key, certificate and provisioning profile to make
the tests pass. 

The key was generated solely for this library, and the certificate is self-signed. A working
key would have to be certified by Apple.

The provisioning profile was created with makeFakePprof.sh and test.mobileprovision.plist. The structure
is based on a real provisioning profile, but all data has been swapped for meaningless noise.
