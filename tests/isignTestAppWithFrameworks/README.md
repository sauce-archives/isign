# isignTestApp

Project to create a very simple test app for isign's test suite.

This is exactly like the isignTestApp, except that if it's working, it should 
also display a lightning bolt on the main screen. 

This app includes Github user @thii's 
[FontAwesome_swift Framework](https://github.com/thii/FontAwesome_swift), 
which crucially for our test, includes both a small resource (a font file) and 
a small amount of code. 

# Prerequisites

This project uses frameworks from the [CocoaPods](http://cocoapods.org) system.
To obtain the frameworks, install Cocoapods, then run `pod install` in this directory.

# Building

Run `./build.sh` to create the necessary test .ipa in the
isign test directory (which is the containing directory).

## Caveats

Currently, the TeamID specified is Neil Kandalgaonkar (neilk@neilk.net)'s' personal
organization ID. For this to work, you would also need a provisioning profile installed 
in the right places on your system (the obvious thing is to use XCode). 

So... you pretty much need to be Neil to build this, unless you modify the `build.sh` 
script and the `exportOptions.plist` in this directory.

For obvious reasons this is a problem going forward. Perhaps we'll need to create some sort
of Apple account which the community can use to sign the test apps. But on the assumption
that we will only need to recreate the test apps very rarely, we're open sourcing it as it is,
for now.
