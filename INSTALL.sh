#!/bin/bash

set -e

REQUIRED_OPENSSL_VERSION="1.0.1"
REQUIRED_PIP_VERSION="7.0.0"
BREW_USER="unknown"
DEVELOP=false

if [[ "$1" == 'develop' ]]; then
    DEVELOP=true
fi


abort_install() {
    warn "Aborting the install. If you want to install prerequisites"
    warn "manually, see PREREQUISITES.rst."
    exit 0;
}

warn() {
    echo "$@" 1>&2;
}

trim() {
    # has the side effect of trimming whitespace
    echo "$@" | xargs
}

get_ok_to_upgrade() {
    warn "This script may install or upgrade the following software:"
    warn "  - brew";
    warn "  - openssl";
    warn "  - libffi"
    warn "  - python and pip";
    warn "  - libimobiledevice and related utilities";
    read -p "Okay to continue? [Y/n]" -n 1 -r 
    warn " " 
    warn " " 
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        abort_install
    fi
}

# given arguments like 1.0.2e, 3, returns "2"
get_version_part() {
    local version=$1
    local part=$2
    echo $version | cut -f $part -d '.' | sed 's/[^0-9]//g'
}

check_version() {
    local required=$1;
    local given=$2;
    local i
    for i in 1 2 3; do
        local required_part=$(get_version_part $required $i);
        local given_part=$(get_version_part $given $i);
        if [[ $given_part -lt $required_part ]]; then
            return 1;
        fi
    done;
    return 0;
}

exists() {
    # warn "checking for existence of $1"
    which $1 > /dev/null
}


openssl_version_ok() {
    local openssl_path=$1
    warn "Trying to check if $openssl_path openssl version is okay..."
    if [[ -e $openssl_path ]]; then
        local openssl_version=$($openssl_path version | cut -f 2 -d ' ');
        warn "Found $openssl_path version $openssl_version."
        if check_version $REQUIRED_OPENSSL_VERSION $openssl_version; then
            warn "$openssl_path version looks okay."
            return 0;
        fi
    fi
    warn "$openssl_path version was not okay!"
    return 1;
}

setup_brew() {
    if exists brew; then
        warn "You seem to have brew."
    else
        # This is what https://brew.sh recommends...
        # Installing straight from a URL? What could go wrong?
        local homebrew_install_url="https://raw.githubusercontent.com/Homebrew/install/master/install"
        warn "We need to install brew..."
        warn "Okay to install via ruby script at this URL?"
        warn "  $homebrew_install_url";
        warn " "
        read -p "Okay to continue? [Y/n]" -n 1 -r 
        warn " " 
        warn " " 
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            abort_install
        fi
        ruby -e "$(curl -fsSL $homebrew_install_url)";
    fi
    # which user owns the Cellar? We'll need this to install things...
    BREW_USER=$(stat -f '%Su' `brew --cellar`)
    warn "brew's stuff seems to be owned by $BREW_USER..."
    return 0;
}

# Commands that write to brew's Cellar need to not be root
brew_write() {
    local command=$1 
    local package=$2
    if [[ $EUID -eq 0 ]]; then
        sudo -u $BREW_USER brew $command $package
    else
        brew $command $package
    fi
}

# some brew packages have this in machine readable form
# but not all :(
brew_get_flags() {
    local package=$1
    local flags=$2
    brew info $package | grep $flags | awk '{print $2}'
}

# check if a program is managed by brew
# it might be a symlink like /usr/local/bin/openssl, pointing to somewhere in the Cellar
is_brew_program() {
    readlink `which $1` | grep `brew --prefix` >/dev/null;
}

mac_setup_openssl() {
    # warn "start mac_setup_openssl"
       
    # if the currently installed openssl doesn't meet our requirements,
    # install or upgrade with brew
    local openssl_path=$(which openssl)
    if [[ -n $openssl_path ]]; then
        if ! openssl_version_ok $openssl_path; then
           brew_setup_openssl
        fi
    fi

    # At this point, the openssl version is okay. It may or may not
    # be a brew installed program. If it is, set up some compilation 
    # library paths. We append to $LDFLAGS and $CPPFLAGS because some other
    # things put flags in there too.
    if is_brew_program openssl; then
        openssl_ldflags=$(brew_get_flags openssl LDFLAGS)
        export LDFLAGS=$(trim "$LDFLAGS $openssl_ldflags")
        openssl_cppflags=$(brew_get_flags openssl CPPFLAGS)
        export CPPFLAGS=$(trim "$CPPFLAGS $openssl_cppflags")
        # Some stackoverflow answers use this too? 
        export CFLAGS=$CPPFLAGS
    fi

    return 0;
}


brew_setup_openssl() {
    # So now we know there either wasn't an openssl, or it wasn't
    # a version good enough. Time for brew!   
 
    # is the brew openssl installed? if not, install
    brew_openssl_path=$(brew list openssl | grep -e '/openssl$')
    # warn "brew openssl path = $brew_openssl_path"
    if [[ -z $brew_openssl_path ]]; then
        warn "Installing openssl..."
        brew_write install openssl
        brew_openssl_path=$(brew list openssl | grep -e '/openssl$')
    fi 
    # warn "brew openssl path = $brew_openssl_path"

    # is the brew openssl the right version? if not, upgrade
    if ! openssl_version_ok $brew_openssl_path; then
        warn "Upgrading openssl..."
        brew_write upgrade openssl
        brew_openssl_path=$(brew list openssl | grep -e '/openssl$')
    fi
    # warn "okay by now $brew_openssl_path should be an acceptable openssl"

    # for various reasons, brew will refuse to simultaneously 
    # be root and link the brew openssl binary somewhere useful. 
    # So we do it manually. We assume that the brew --prefix will be 
    # in the user's $PATH, and will take precedence over system openssl. 
    brew_link_path=$(brew --prefix)/bin/openssl
    # warn "brew link path is $brew_link_path"
    if [[ -e brew_link_path ]]; then
        # warn "removing existing link"
        rm brew_link_path;
    fi
    warn "Linking $brew_openssl_path $brew_link_path."
    ln -s $brew_openssl_path $brew_link_path

    # let's see if we succeeded: the openssl in our path should now be ready!
    new_openssl_path=$(which openssl)
    # warn "new path is $new_openssl_path"
    if ! openssl_version_ok $new_openssl_path; then
        warn "We tried to install an openssl >$MINIMUM_OPENSSL_VERSION, but we failed."
        warn "Check if $brew_link_path is in your \$PATH ($PATH)."
        return 1
    fi
    # warn "success, finally"

    return 0;
}

mac_setup_libffi() {
    warn "Checking for libffi..."
    if ! brew list libffi 2>/dev/null >/dev/null; then
        warn "Nope, no libffi. Installing..."
        brew_write install libffi
    fi
    # set up some compilation library paths (we'll need it later...)
    local libffi_ldflags=$(brew_get_flags libffi LDFLAGS)
    export LDFLAGS=$(trim "$LDFLAGS $libffi_ldflags")
}

mac_setup_python() {
    if exists pip; then
        pip_version=$(pip --version | awk '{ print $2 }')
        if check_version $REQUIRED_PIP_VERSION $pip_version; then
            warn "pip version $pip_version looks okay."
            return 0;
        fi
    fi
    brew_write install python
}

mac_setup_libimobiledevice() {
    if exists ideviceinstaller; then
        return 0;
    fi
    brew_write install libimobiledevice
}

mac_setup() {
    get_ok_to_upgrade
    setup_brew
    mac_setup_openssl
    mac_setup_libffi
    mac_setup_python
    mac_setup_libimobiledevice
}

linux_setup() {
    #apt-get install ideviceinstaller
    #apt-get install libimobiledevice-utils
    echo "Skipping apt-get installs, we use yum"
}


unamestr=`uname`
if [[ "$unamestr" == 'Darwin' ]]; then
    mac_setup
elif [[ "$unamestr" == 'Linux' ]]; then
    linux_setup
else
    warn "Sorry, I don't know how to install on $unamestr.";
    exit 1;
fi;

echo "--- Flags ---"
echo "LDFLAGS=$LDFLAGS"
echo "CPPFLAGS=$CPPFLAGS"
echo "CFLAGS=$CFLAGS"
echo

if [[ "$DEVELOP" == true ]]; then
    python setup.py develop
else
    python setup.py install
fi
