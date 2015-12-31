Apple developer credentials
===========================

Mac OS X and iOS aren't like most other operating systems -- security is baked into every
single program. The machine is able to check, before it even executes the program, who
wrote it, whether Apple approved it, and whether it has the authority to do some things 
that it's asking to do. On Mac OS X, it's easy to get around those restrictions, but iOS 
is locked down very tight.

The iOS device is able tell who wrote a program, and whether Apple approved it, without
even phoning home to Apple. It does this by looking for evidence that is *was* approved 
at some earlier date, using cryptographic signatures embedded right into the application. 

Until now, few people outside Apple had a full understanding of how that worked, or how to
add that magic "code signature" and other necessary proofs to the app.

``isign`` is able to create those -- with the right credentials.

Definitions
-----------

The **key** is the developer's private key. If you're familiar with Secure Shell keys, this is similar -- it's
the private half of a public-private key pair. The private key is used to sign the application. This proves that
the developer approved the entire contents of the application.

Note that this key is not revealed to Apple, or anyone else. If you
develop iOS apps, you, or someone in your organization, generated such a key. Hopefully they kept it
secret. However, you need it to sign the app -- you probably have it in Keychain Access or something like
that.

The **certificate** is how Apple indicates that the developer is approved to write apps for iOS. At some
point, they signed the public half of the developer's keys. Apple will also encode when your developer account
is going to expire.

The **organizational unit** is an identifier that Apple assigns to organizations that
create apps on Apple devices. It's an eight character code of letters and numbers. You may need to know your 
organizational unit, so you can sign apps from your organization. ``isign`` can extract this from other files,
like your certificate, so you probably don't need to worry about this.

The **provisioning profile** is where it all comes together. This file is included in the app.

The provisioning profile includes the contents of the certificate -- possibly many certificates.
It also includes the UDIDs of the devices that you have registered with Apple. So, you can often use the same
provisioning profile for all your developers and all your iOS devices.

So, when a phone encounters an app, it will start by reading the provisioning profile, to learn things like:

- Who wrote this app?
- What organization do they belong to?
- Are they still an Apple-approved developer?
- And what's their public key?
- Is this app approved to run on this particular device?

From there it can go on to cryptographically verify each and every part of the app. This ensures that the 
app has not been tampered with, or that an unapproved developer hasn't snuck an app onto your phone (even if 
that developer is you.)


How to create Apple developer credentials
-----------------------------------------

For most developers, XCode takes care of most of these credentials. But with ``isign`` you have to do it more manually.
 
Getting an account
~~~~~~~~~~~~~~~~~~

First, find an administrator for your developer organization at Apple. (If you're a solo developer, that's you.)

Get them to invite you to your Apple Organizational Unit. 

You'll get email from Apple, which will prompt you to set up your account. Set up passwords and so on as usual.

Troubleshooting: you may have to click on the mailed invite link
once to set up your account, and then return to your mail to click
on that invite link again to actually activate your account. Also,
in general, things on the Apple site work better with Safari, so
if something doesn't work, try that browser.

Setting up credentials
~~~~~~~~~~~~~~~~~~~~~~

The following procedure works as of June 2015, for adding a new
account from scratch. You will need a Mac OS X computer. (In theory 
you could do this entirely from Linux, using the Apple website, but 
you're on your own there.)

Log into your Apple account.

Go to **Certificates, Identifiers, & Profiles**.

Go to **Certificates > Development** in the left-hand column.

Press the plus icon to add a new certificate.

It will ask what type of certificate you need. You probably want
*iOS App Development*.

It will then instruct you to use Keychain Access to generate a
Certificate Signing Request. In effect you are going to create a
private/public key pair, and then make a little file that says "Hey
Apple, please sign the public half and make a certificate for it, and 
associate that with my Apple account!"

Follow the instructions and save that CSR to disk. Press **Continue**.

Then, the Apple website will ask you to upload that CSR. Do so, and
it will create a certificate for your account in your organization.
This certificate might need to be approved by an admin before you
can download it.

Once it's approved, download it!

It will probably be named something generic like ``ios_development.cer``,
so rename it to something more meaningful and put it somewhere safe.

Import that ``.cer`` into Keychain. Keychain will detect that it
has an associated private key, and in views where you see keys, the
certificate will be "inside" the key, and vice versa.

Provisioning profile
~~~~~~~~~~~~~~~~~~~~

Now we just need to tell Apple that your user is allowed to deploy on those devices. 

First, go to **Devices**, and add the UDIDs of all the devices you care about. If you installed `libimobiledevice`, an easy way to get the
UDID is with ``idevice_id -l``. 

In the Developer portal, go to **Provisioning Profiles**, and create a new development profile. Select those devices and add them.

In **Select App ID**, you probably want to just create one with a
wildcard (Something using your Apple Organizational Unit plus domain plus dot-star, maybe, 
like ``A1B2C3D4.tld.domain.*`` )

Next, in **'Select certificates'**, select the certificates you want, which probably includes the one we just created above.

Finally, download this provisioning profile, and follow the instructions in the main README.
