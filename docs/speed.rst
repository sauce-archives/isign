So you want to make it go faster
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Re-signing is largely about hashing the entire contents of the application. For data that we've
never seen before, we can't do better than O(n).

But we could still do better in the general case:

- There are many files within the application. If we don't touch a file (it's not an executable 
  or dylib), and we got a hash in the app's existing CodeResources seal, we could trust it, and 
  reuse it in our CodeResources seal.

- We could recognize common libraries such as the Swift framework, and keep re-signed versions of 
  those in some persistent storage.

- Use separate processes to hash files, to exploit multiple cores.
