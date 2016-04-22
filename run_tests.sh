#!/bin/bash -e
name=$(basename $PWD)
package=$(echo $name | sed 's/-/_/g')

# look for required apps
for app in unzip zip; do
    if ! which $app >/dev/null; then
        echo "Missing application: $app"
        exit 1
    fi
done

# run test suite
find . -name '*.pyc' -delete
pushd tests >/dev/null
version=$(python -c "import $package; print ${package}.__version__")
echo "Testing $name v${version}"
nosetests
popd >/dev/null
