The test credentials in this directory cannot be used to sign apps for use on any iOS device. They
are sufficiently similar to a real key, certificate and provisioning profile to make
the tests pass. 

The key was generated solely for this library, and the certificate is self-signed. A working
key would have to be certified by Apple.

The provisioning profile is a dummy file, because it isn't actually parsed at any point
during signing. It is simply included in the newly resigned app. 
