#! /bin/bash
#
# deploy.sh
# Copyright (C) 2015 dhilipsiva <dhilipsiva@gmail.com>
#
# Distributed under terms of the MIT license.
#


bumpversion patch
git push
git push --tags 
rm -rf dist/
python setup.py sdist
# python setup.py bdist_wheel
twine upload dist/*
