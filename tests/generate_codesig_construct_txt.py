# generate a string representation of a signature parse for an app - do this to generate
# test files such as Test.app.codesig.construct.txt

from isign_base_test import IsignBaseTest
import isign.archive
from isign.signable import Executable

import logging

FORMATTER = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def log_to_stderr(level=logging.INFO):
    root = logging.getLogger()
    root.setLevel(level)
    handler = logging.StreamHandler()
    handler.setFormatter(FORMATTER)
    root.addHandler(handler)


log_to_stderr(logging.DEBUG)
log = logging.getLogger(__name__)
log.debug("generating a signature parse for an app")
app = isign.archive.AppArchive(IsignBaseTest.TEST_APP)
executable = Executable(app.get_executable_path())
arch = executable.arches[0]
codesig_str = str(arch['cmds']['LC_CODE_SIGNATURE'])
print codesig_str
