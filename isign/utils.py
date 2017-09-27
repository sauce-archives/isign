#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# vim: fenc=utf-8
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
#
#

"""
File name: utils.py
Author: dhilipsiva <dhilipsiva@gmail.com>
Date created: 2016-06-07
"""

import binascii


def decode_dict(source):
    """
    docstring for
    """
    if type(source) in [str, int, float, bool]:
        return source
    if type(source) == bytes:
        return source.decode()
    if type(source) in [list, set]:
        decode_list = []
        for item in source:
            decode_list.append(decode_dict(item))
        return decode_list
    target = {}
    for key, value in source.items():
        key = decode_dict(key)
        value = decode_dict(value)
        target[key] = value
    return target


def print_data(data):
    hexstring = binascii.hexlify(data)
    n = 80
    split_string = "\n".join([hexstring[i:i+n] for i in range(0, len(hexstring), n)])
    print(split_string)


def round_up(x, k):
    return ((x + k - 1) & -k)


def print_structure(container, struct):
    actual_data = struct.build(container)
    return "{}".format(struct.parse(actual_data))
