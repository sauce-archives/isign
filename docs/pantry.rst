Pantry
~~~~~~

isign was designed to work with the Pantry system, also known as Sauce Storage. 

We are getting Pantry to examine every incoming file to see if it's an iOS native app, and if it is, creates a file that should work on our 
iOS devices. 

isign expects there to be credentials already installed in ``~sauce/isign-credentials``. We deploy the right credentials to the 
right environment with our ``sauce-ansible`` system, with the ``isign`` role.

If you want to test this aspect of Pantry, see `How to simulate Pantry on a stew <https://saucedev.atlassian.net/wiki/display/AD/How+to+simulate+Pantry+on+a+stew>`__ for more.
