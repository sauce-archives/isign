import binascii


def print_data(data):
    hexstring = binascii.hexlify(data)
    n = 80
    split_string = "\n".join([hexstring[i:i+n] for i in range(0, len(hexstring), n)])
    print split_string


def round_up(x, k):
    return ((x + k - 1) & -k)


def print_structure(container, struct):
    actual_data = struct.build(container)
    return "{}".format(struct.parse(actual_data))

