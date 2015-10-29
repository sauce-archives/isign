
keys and certificates


If you don't have these files already, you should get them from our Ansible repo. If not,
read on for how to create them from scratch.


Getting credentials from Ansible
================================

You can obtain these from the ``isign_creds`` role in the ``sauce-ansible`` repository. The files
are encrypted there. Just run the associated task with ansible, and it 
should drop the proper files into your home directory. 

There are three different sets of credentials: development, build test, and production.
For simplicity, when they are exported out of ansible, they all get the same filenames, 
but they have different contents. The identities are associated with a pseudo-user in our
"Organizational Unit" in Apple, and each have their own Apple Developer Accounts. The 
.mobileprovision files tie the credentials to different sets of devices.

**Development** - pseudo-user called "Moby Dev", associated with the mail alias
``mobdev@saucelabs.com``, which goes to all the mobile developers at Sauce Labs.

**Build Test** - pseudo-user called "Bill D. Tester", associated with
``neilk+buildtest@saucelabs.com`` for now. Possibly it will be ``mobbuild@saucelabs.com`` by the time
you read this. That email should be available to all mobile developers at Sauce 
Labs. We use 'buildtest.mobileprovision' to hold
the UDIDs of the devices attached to the build-somen.

**Production** is associated with "Moby Prod", associated with 
``neilk+mobprod@saucelabs.com`` for now. Possibly it will be ``mobprod@saucelabs.com`` by the time
you read this, which would go to all mobile developers plus some operations people. 
We don't have any .mobileprovision yet because there aren't any devices in a production RDC yet.

Look in Passpack for the passwords to the associated Apple Developer accounts.


Getting credentials from Apple
==============================

 First, find an administrator for our developer organization at
Apple. At this moment, @neilk, @filmaj, and @admc are all admins. Get
them to invite you to the organization under your @saucelabs.com
account, in the iOS Developer Program.

