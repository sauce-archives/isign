Rationale
=========

So, why does this library even exist?

The iOS kernel will refuse to run an app if it doesn't have an
appropriate signature that it can trace, in various ways, all the way
back to Apple.

This signature is built right into the format of how executables are
laid out on iOS, the LC\_CODE\_SIGNATURE structure in a Mach-O binary.

Apps from the app store are already signed in a way that allows them to
run on any computer. Developers need to get a special 'provisioning' file
from Apple to test their apps on their devices.

It's relatively easy to re-sign an app using Apple tools -- see the
``apple`` directory in this repo for sample scripts. Pretty much everyone
else that has needed to do this just uses a Mac anyway. Even if their
build system is Linux-based, they will add a Mac to that somehow, and
ssh into it to do signing.

Sauce Labs now offers testing on `real iOS devices <https://saucelabs.com/press-room/press-releases/sauce-labs-expands-mobile-test-automation-cloud-with-the-addition-of-real-devices-1>`__. 
Customers can upload apps they are developing, and we run the tests on a real iPhone.

So we have the problem that our customers' apps are
almost certainly provisioned only for their devices. But they need to
run on our devices.

We needed to do signing at scale, and we wanted to avoid the
various problems of adding Mac hardware to our cloud infrastructure (particularly
licensing). It turns out that while it was really hard, it's
possible to sign apps using entirely open source tools.

Sauce Labs is a company with open source DNA, so we knew once we had solved
this problem we put it on our roadmap to open source this library. On the more 
strategic side, we also would like it if we had more of a community around this 
code, so we wouldn't be on our own if Apple ever changes this format. We've heard
that we aren't the only ones who have solved this problem, but everyone else is
working alone and not contributing back to the community. Hopefully this library 
will change that.

In the meantime, we've been running this in our production cloud for months, and
it's been happily processing customers' tests. We hope you find it useful.
