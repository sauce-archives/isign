So you want to make it go faster
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The *vast* majority of time in isign is not spent signing. It's in zipping and re-zipping. 

Most apps are packaged as IPAs. These are just glorified zip files with a particular directory structure. For most situations, we can't avoid the cost of unzipping and re-zipping. So if we're trying to make it faster, we've already lost, since we'll never speed it up even by a factor of 2. 

In theory you could:

- Not use IPAs. isign can also re-sign unzipped ".app" directories. This is way faster, but then you have to use isign where you created the app, and you have to install the resigned app onto a device from there as well.

- Use IPAs but re-compress them poorly. Basically, change the setting from zip quality of 6 (the default) to something else. Minor speedups can be accomplished that way, at the cost of increasing install time or time to transfer to send it the network. In my tests it wasn't an improvement when you considered typical things you would do with the app next.

If neither of those approaches is acceptable to you, you can stop reading here. Because everything else that follows will speed it up, but not by much.


Okay, so what *else* is taking time?

1) Copying the files. Maybe with some exotic copy-on-write filesystem we could avoid that?

2) Hashing the entire contents of the application. For data that we've never seen before, we can't do better than O(n). So we lose *again*.

But we could still do better in the general case:

- There are many files within the application. If we don't touch a file (it's not an executable 
  or dylib), and we got a hash in the app's existing CodeResources seal, we could trust it, and 
  reuse it in our CodeResources seal. 
  
  I tried implementing this and it was super annoying to code, and didn't
  have a big impact on my test files, so I gave up. The problem is that you have to write wrappers around 
  every method that writes to a file, and keep a tally of what files you touched. If you don't mind a less
  accurate method (scan directories for files changed since the start of the resigning process) that 
  might work better.

- We could recognize common libraries such as the Swift framework, and keep re-signed versions of 
  those in some persistent storage.

- Use separate processes to hash files, to exploit multiple cores.

But wait!
~~~~~~~~~

Incidentally, if what you're looking for is to resign one app with multiple credentials, look into the `multisign` scripts. There can save a significant amount of time by unzipping the original app only once, and using a process pool to exploit multiple cores.
