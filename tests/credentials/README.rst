These credentials are associated with the user named "Jenkins Sauce", email address
<neilk+jenkins@saucelabs.com>. They are meant for running automated tests, while
developing, but especially in continuous integration (hence, Jenkins).

This should be a very underpowered user, different from the certificates we use that
can actually install things into the development or production Real Device Cloud. 
It has just enough power to sign an app and the provisioning profile lets us install
an app on the iPhone 6 in Vancouver. (If I could have had an "empty" provisioning 
profile I would have done that.)
