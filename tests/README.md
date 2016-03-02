To test isign, we need to actually sign some apps. This directory contains
the tests and the test data AND the source files to generate that test data.

This directory includes a lot of stuff. It could probably be better organized.

Test data: to check that the library can detect non-apps:
* NotAnApp.ipa
* NotAnApp.txt

Test data - compiled apps:
* Test.app
* Test.app.zip
* Test.ipa
* TestSimulator.app.zip
* TestWithFrameworks.ipa

Expected data from apps:
* Test.app.codesig.construct.txt

A short program to generate that expected data:
* generate_codesig_construct_txt.py

A test file, to see what happens when "helper" apps go wrong:
* bad_openssl

Self-signed/fake credentials, to make these tests even work
* credentials

Source to build the test apps:
* isignTestApp
* isignTestAppWithFrameworks

Helper for tests:
* `monitor_temp_file.py`
* `helpers.py`

Actual test code:
* `isign_base_test.py`
* `test_*.py:`   
