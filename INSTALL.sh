#!/bin/bash

set -e

REQUIRED_OPENSSL_VERSION="1.0.1"
MAC_INSTALL_PATH="/usr/local/bin"


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
    echo "We're about to install or upgrade the following software:"
    if [[ $has_brew ]]; then
        echo "  - brew";
    fi
    if [[ $has_openssl ]]; then
        echo "  - openssl";
    fi
    if [[ $has_libffi ]]; then
        echo "  - libffi"
    fi
    if [[ $has_pip ]]; then
        echo "  - python and pip";
    fi
    read -p "Okay to continue? [Y/n]" -n 1 -r 
    echo
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
    which $1 > /dev/null;
}


openssl_version_ok() {
    if exists openssl; then
        openssl_version=$(openssl version | cut -f 2 -d ' ');
        if check_version $REQUIRED_OPENSSL_VERSION $openssl_version; then
            return 0;
        fi
    fi
    return 1;
}

setup_brew() {
    if exists brew; then
        return 0;
    else
        echo "installing brew..."
        # from brew.sh
        ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)";
    fi
}

brew_install() {
    package=$1
    if [[ $EUID -eq 0 ]]; then
        # brew doesn't like to install stuff as root.
        # On Mac OS X, there will be an environment variable called $SUDO_USER for us to 
        # switch back to.
        sudo -u $SUDO_USER brew install $package
    else
        brew install $package
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
    if [[ ! openssl_version_ok ]]; then
        brew_install openssl
        # For some reason this package won't install openssl into our path, so we have 
        # to do a symlink manually.
        # If there is an old openssl, We could try to move it manually (we are root) but
        # often it's locked. So let's just advise them to set up the path properly
        if exists openssl; then
            old_openssl_dir=$(which openssl | xargs dirname)
            warn "========="
            warn "IMPORTANT: you still have an old openssl in $old_openssl_dir. The new one is in $MAC_INSTALL_PATH."
            warn "So, ensure that $MAC_INSTALL_PATH is ahead of $old_openssl_dir in your \$PATH."
            warn "========="
        fi
        openssl_brew_path=$(brew list openssl | grep -e '/openssl$')
        ln -s $openssl_brew_path "$MAC_INSTALL_PATH/openssl"
    fi
    # set up some compilation library paths (we'll need it later...)
    openssl_ldflags=$(brew_get_flags openssl LDFLAGS)
    LDFLAGS=$(trim "$LDFLAGS $openssl_ldflags")
    openssl_cppflags=$(brew_get_flags openssl CPPFLAGS)
    CPPFLAGS=$(trim "$CPPFLAGS $openssl_cppflags")
}

mac_setup_libffi() {
    if ! brew list libffi > /dev/null; then
        brew_install libffi
    fi
    # set up some compilation library paths (we'll need it later...)
    libffi_ldflags=$(brew_get_flags libffi LDFLAGS)
    LDFLAGS=$(trim "$LDFLAGS $libffi_ldflags")
}

mac_setup_python() {
    if exists pip; then
        return 0;
    fi
    brew install python
}

mac_setup_libimobiledevice() {
    if exists ideviceinstaller; then
        return 0;
    fi
    brew install libimobiledevice
}

setup_mac() {
    setup_brew
    mac_setup_openssl
    mac_setup_libffi
    mac_setup_python
    mac_setup_libimobiledevice
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


