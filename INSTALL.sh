#!/bin/bash

set -e

REQUIRED_OPENSSL_VERSION="1.0.1"
BREW_USER="unknown"

install_package() {
    python setup.py install
}

setup_linux() {
    install_package
    apt-get install ideviceinstaller
    apt-get install libimobiledevice-utils
}

warn() {
    echo "$@" 1>&2;
}

trim() {
    # has the side effect of trimming whitespace
    echo "$@" | xargs
}

check_what_to_upgrade() {
    has_brew=`which brew`
    has_openssl=`which openssl`
    has_libffi=`which libffi`
}


ok_to_upgrade() {
    warn "We're about to install or upgrade the following software:"
    if [[ $has_brew ]]; then
        warn "  - brew";
    fi
    if [[ $has_openssl ]]; then
        warn "  - openssl";
    fi
    if [[ $has_libffi ]]; then
        warn "  - libffi"
    fi
    if [[ $has_pip ]]; then
        warn "  - python and pip";
    fi
    read -p "Okay to continue? [Y/n]" -n 1 -r 
    warn "" 
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        exit 0;
    fi
}

# given arguments like 1.0.2e, 3, returns "2"
get_version_part() {
    version=$1
    part=$2
    echo $version | cut -f $part -d '.' | sed 's/[^0-9]//g'
}

check_version() {
    required=$1;
    given=$2;
    for i in 1 2 3; do
        required_part=$(get_version_part $required $i);
        given_part=$(get_version_part $given $i);
        if [[ $given_part -lt $required_part ]]; then
            return 1;
        fi
    done;
    return 0;
}

exists() {
    warn "checking for existence of $1"
    which $1 > /dev/null;
    return $?
}


openssl_version_ok() {
    openssl_path=$1
    warn "trying to check if $openssl_path openssl version is okay"
    if [[ -e $openssl_path ]]; then
        openssl_version=$($openssl_path version | cut -f 2 -d ' ');
	warn "found $openssl_path version $openssl_version"
        if check_version $REQUIRED_OPENSSL_VERSION $openssl_version; then
            warn "okay!"
            return 0;
        fi
    fi
    warn "not okay!"
    return 1;
}

setup_brew() {
    if exists brew; then
	warn "you have brew"
    else
        warn "installing brew..."
        # from brew.sh
        ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)";
    fi
    # which user owns the Cellar? We'll need this to install things...
    BREW_USER=$(stat -f '%Su' `brew --cellar`)
    warn "BREW_USER is $BREW_USER"
    return 0;
}

brew_command() {
    command=$1 
    package=$2
    if [[ $EUID -eq 0 ]]; then
        # brew doesn't like to install stuff as root.
        # On Mac OS X, there will be an environment variable called $SUDO_USER for us to 
        # switch back to.
        sudo -u $BREW_USER brew $command $package
    else
        brew $command $package
    fi
}

# some brew packages have this in machine readable form
# but not all :(
brew_get_flags() {
    package=$1
    flags=$2
    brew info $package | grep $flags | awk '{print $2}'
}

mac_setup_openssl() {
    warn "start mac_setup_openssl"
   
       
    # early return if the currently installed openssl meets our requirements
    # (it probably won't)
    openssl_path=$(which openssl)
    if [[ -n $openssl_path ]]; then
        if openssl_version_ok $openssl_path; then
           # openssl is fine! do nothing.
           return 0;
        fi
    fi

    # So now we know there either wasn't an openssl, or it wasn't
    # a version good enough. Time for brew!   
 
    # is the brew openssl installed? if not, install
    brew_openssl_path=$(brew list openssl | grep -e '/openssl$')
    warn "brew openssl path = $brew_openssl_path"
    if [[ -z $brew_openssl_path ]]; then
    	warn "installing openssl"
        brew_command install openssl
        brew_openssl_path=$(brew list openssl | grep -e '/openssl$')
    fi 
    warn "brew openssl path = $brew_openssl_path"

    # is the brew openssl the right version? if not, upgrade
    if ! openssl_version_ok $brew_openssl_path; then
    	warn "upgrading openssl"
        brew_command upgrade openssl
        brew_openssl_path=$(brew list openssl | grep -e '/openssl$')
    fi
    warn "okay by now $brew_openssl_path should be an acceptable openssl"

    # for various reasons, brew will refuse to simultaneously 
    # be root and link the brew openssl binary somewhere useful. 
    # So we do it manually. We assume that the brew --prefix will be 
    # in our $PATH, and will take precedence over system openssl. 
    brew_link_path=$(brew --prefix)/bin/openssl
    warn "brew link path is $brew_link_path"
    if [[ -e brew_link_path ]]; then
    	warn "removing existing link"
        rm brew_link_path;
    fi
    warn "linking $brew_openssl_path $brew_link_path"
    ln -s $brew_openssl_path $brew_link_path

    # let's see if we succeeded: the openssl in our path should now be ready!
    new_openssl_path=$(which openssl)
    warn "new path is $new_openssl_path"
    if ! openssl_version_ok $new_openssl_path; then
        warn "We tried to install an openssl >$MINIMUM_OPENSSL_VERSION, but we failed."
        warn "Check if $brew_link_path is in your \$PATH ($PATH)."
        return 1
    fi
    warn "success, finally"

    # set up some compilation library paths (we'll need it later...)
    openssl_ldflags=$(brew_get_flags openssl LDFLAGS)
    LDFLAGS=$(trim "$LDFLAGS $openssl_ldflags")
    openssl_cppflags=$(brew_get_flags openssl CPPFLAGS)
    CPPFLAGS=$(trim "$CPPFLAGS $openssl_cppflags")

    return 0;
}

mac_setup_libffi() {
    warn "checking for libffi"
    if ! brew list libffi 2>/dev/null >/dev/null; then
        warn "nope no libffi"
        brew_command install libffi
    fi
    # set up some compilation library paths (we'll need it later...)
    libffi_ldflags=$(brew_get_flags libffi LDFLAGS)
    LDFLAGS=$(trim "$LDFLAGS $libffi_ldflags")
}

mac_setup_python() {
    if exists pip; then
        return 0;
    fi
    brew_command install python
}

mac_setup_libimobiledevice() {
    if exists ideviceinstaller; then
        return 0;
    fi
    brew_command install libimobiledevice
}

setup_mac() {
    warn "setup_brew"
    setup_brew
    warn "mac_setup_openssl"
    mac_setup_openssl
    warn "mac_setup_libffi"
    mac_setup_libffi
    warn "mac_setup_python"
    mac_setup_python
    warn "mac_setup_libimobiledevice"
    mac_setup_libimobiledevice
    warn "ldflags: $LDFLAGS"
    warn "cppflags: $CPPFLAGS"
    warn "install_package"
    install_package
}

unamestr=`uname`
if [[ "$unamestr" == 'Darwin' ]]; then
    setup_mac
elif [[ "$unamestr" == 'Linux' ]]; then
    setup_linux
else
    warn "Sorry, I don't know how to install on $unamestr.";
    exit 1;
fi;


