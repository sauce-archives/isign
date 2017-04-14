import logging
import macho_debug
import os
import sys
import utils

log = logging.getLogger(__name__)

def main(path):
    file_end = 0
    f = open(path, "rb")



    m = macho_debug.MachoFile.parse_stream(f)
    print("path {}: {}".format(path, m))

#    f.seek(0x1000)
#    actual_data_slice = f.read(0x1000)
#    utils.print_data(actual_data_slice)


    f.close()



if __name__ == '__main__':
    main(sys.argv[1])