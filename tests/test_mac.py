import distutils
from os.path import abspath
from os.path import dirname
from os.path import join
import platform
import pprint
import pytest
import re
import subprocess

CODESIGN_BIN = distutils.spawn.find_executable('codesign')
TEST_APP = join(dirname(__file__), 'apps', 'NativeIOSTestApp.app')
PROVISIONS_BIN = join(dirname(dirname(abspath(__file__))),
                      'provisions.py')


@pytest.mark.skipif(platform.system() != 'Darwin' or CODESIGN_BIN is None,
                    reason="need a Mac with codesign to run")
class TestMac:
    def codesign_display(self, path):
        """ inspect a path with codesign """
        cmd = [CODESIGN_BIN, '-d', '-r-', '--verbose=20', path]
        # n.b. codesign usually prints everything to stderr
        proc = subprocess.Popen(cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        out, _ = proc.communicate()
        assert proc.returncode == 0, "Return code not 0"
        return self.codesign_display_parse(out)

    def codesign_display_parse(self, out):
        """
        Parse codesign output into a dict.

        The output format is XML-like, in that it's a tree of nodes of
        varying types (including key-val pairs). We are assuming that
        it never gets more than 1 level deep (so, "array line" is just
        a special case here)
        """

        # designated => identifier "com.lyft.ios.enterprise.dev" and anchor...
        text_line = re.compile('^(\w[\w\s.]+) => (.*)$')

        # CodeDirectory v=20200 size=79151 flags=0x0(none) hashes=3948+5 ...
        props_line = re.compile('^(\w[\w\s.]+)\s+((?:\w+=\S+\s*)+)$')

        # Signed Time=May 14, 2015, 7:12:25 PM
        # Info.plist=not bound
        single_prop_line = re.compile('(\w[\w\s.]+)=(.*)$')

        # this assumes we only have one level of sub-arrays
        #    -3=969d263f74a5755cd3b4bede3f9e90c9fb0b7bca
        array_line = re.compile('\s+(-?\d+)=(.*)$')

        # last node assigned - used for appending sub-arrays, if encountered
        last = None

        ret = {}

        for line in out.splitlines():
            key = None
            val = None
            text_match = text_line.match(line)
            props_match = props_line.match(line)
            sp_match = single_prop_line.match(line)
            array_match = array_line.match(line)
            print line
            if text_match:
                key = text_match.group(1)
                val = text_match.group(2)
            elif props_match:
                key = props_match.group(1)
                val = {}
                pairs = re.split('\s+', props_match.group(2))
                for pair in pairs:
                    pairmatch = re.match('(\w+)=(\S+)', pair)
                    pairkey = pairmatch.group(1)
                    pairval = pairmatch.group(2)
                    val[pairkey] = pairval
            elif sp_match:
                key = sp_match.group(1)
                val = sp_match.group(2)
            elif array_match:
                if '_' not in last:
                    last['_'] = {}
                akey = array_match.group(1)
                aval = array_match.group(2)
                last['_'][akey] = aval
            else:
                # probably an error of some kind. These
                # get appended into the output too. :(
                if '_errors' not in ret:
                    ret['_errors'] = []
                ret['_errors'].append(line)
            if key is not None:
                ret[key] = val
                last = ret[key]

        return ret

    def test_niota(self):
        cmd = [PROVISIONS_BIN,
               '-p', '/Users/neilk/neilkprofile.mobileprovision',
               # TODO cert arg
               '-o', 'test-out.app',
               TEST_APP]
        print ' '.join(cmd)
        proc = subprocess.Popen(cmd)
        proc.communicate()
        assert proc.returncode == 0, "Return code not 0"
        out = self.codesign_display('test-out.app')
        return out


if __name__ == '__main__':
    x = TestMac()
    pp = pprint.PrettyPrinter(indent=2)
    pp.pprint(x.test_niota())
