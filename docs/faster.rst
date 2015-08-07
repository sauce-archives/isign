So you want to make it go faster
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Re-signing is largely about hashing the entire contents of the application. For data that we've
never seen before, we can't do better than O(n).

But we could still do better in the general case:

1) There are many files within the application. If we don't touch a file (it's not an executable 
   or dylib), and we got a hash in the app's existing CodeResources seal, we could trust it, and 
   reuse it in our CodeResources seal.

2) We could recognize common libraries such as the Swift framework, and keep re-signed versions of 
   those in some persistent storage.

3) We could cache entire re-signed apps. It's possible that sometimes the customer will upload
   the exact same app as last time, with a modified test. Pantry already takes the MD5 of the entire
   file, so we could use that as a cache key.

4) Use separate processes to hash files, to exploit multiple cores.
