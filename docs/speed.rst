So you want to make it go faster
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Most apps are packaged as IPAs. These are just glorified zip files with a particular directory structure.
The *vast* majority of time in isign is spent unzipping and re-zipping them. For most situations this is unavoidable, since IPAs are the most convenient way to move an app around.

In theory you could:
- Not use IPAs. isign can also re-sign unzipped ".app" directories. 
- Use IPAs but re-compress them poorly. Basically, change the setting from zip quality of 6 (the default) to something else. Minor speedups can be accomplished that way, at the cost of increasing install time or time to transfer it over the network. Generally this is not worth it, so it's not an option.

Okay, so what *else* can we do?

After that, the majority of the time re-signing is about hashing the entire contents of the application. For data that we've
never seen before, we can't do better than O(n). So we lose *again*.

But we could still do better in the general case:

- There are many files within the application. If we don't touch a file (it's not an executable 
  or dylib), and we got a hash in the app's existing CodeResources seal, we could trust it, and 
  reuse it in our CodeResources seal. I tried implementing this and it was super annoying to code, and didn't
  have a big impact on my test files, so I gave up. The problem is that you have to write wrappers around 
  every method that writes to a file, and keep a tally of what files you touched. If you don't mind a less
  accurate method (scan directories for files changed since the start of the resigning process) that 
  might work better.

- We could recognize common libraries such as the Swift framework, and keep re-signed versions of 
  those in some persistent storage.

- Use separate processes to hash files, to exploit multiple cores.

Incidentally, if what you're looking for is to resign one app with multiple credentials, look into the `multisign` scripts. There we save time by unzipping the original app only once.
