# isignTestApp

Project to create a very simple test app for isign's test suite.

Run `./build.sh` to create the necessary test app, app.zip, .ipa, and simulator app in the
isign test directory (which is the containing directory).

## Caveats

Currently, the TeamID specified is Neil Kandalgaonkar (neilk@neilk.net's) personal
organization ID. For this to work, you would also need a provisioning profile installed 
in the right places on your system (the obvious thing is to use XCode). So... you pretty
much need to be Neil to build this, unless you modify the `build.sh` script.

For obvious reasons this is a problem going forward - we'll need to create some sort
of Apple account which the community can use to sign the test apps. But on the assumption
that we will only need to recreate the test apps very rarely, we're open sourcing it as it is,
for now.
