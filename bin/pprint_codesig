#!/usr/bin/env python

import argparse
import isign.app
from isign.signable import Executable
import logging
from os.path import abspath, expanduser, isdir
import pprint
import shutil

FORMATTER = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)
pp = pprint.PrettyPrinter(indent=4, width=1000)


def log_to_stderr(level=logging.INFO):
    root = logging.getLogger()
    root.setLevel(level)
    handler = logging.StreamHandler()
    handler.setFormatter(FORMATTER)
    root.addHandler(handler)


def absolute_path_argument(path):
    return abspath(expanduser(path))


def print_codesig(path):
    temp_dir = None
    try:
        appArchive = isign.app.app_archive_factory(path)
        (temp_dir, app) = appArchive.unarchive_to_temp()
        _print_codesig(app)
    except isign.app.NotSignable as e:
        msg = "Not signable: <{0}> {1}\n".format(path, e)
        log.error(msg)
        raise
    finally:
        if temp_dir is not None and isdir(temp_dir):
            shutil.rmtree(temp_dir)


def _print_codesig(app):
    executable = Executable(app.get_executable_path())
    for arch in executable.arches:
        pp.pprint(arch['cmds']['LC_CODE_SIGNATURE'])


def parse_args():
    parser = argparse.ArgumentParser(
        description='Print the code signature structure of an executable or dylib')
    parser.add_argument(
        '-v', '--verbose',
        dest='verbose',
        action='store_true',
        default=False,
        required=False,
        help='Set logging level to debug.'
    )
    parser.add_argument(
        'app_paths',
        nargs=1,
        metavar='<app path>',
        type=absolute_path_argument,
        help='Path(s) to application, typically a '
             'directory ending in .app or file ending in .ipa.'
    )
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()
    if args.verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
    log_to_stderr(level)

    print_codesig(args.app_paths[0])
