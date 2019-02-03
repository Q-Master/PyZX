# -*- coding: utf-8 -*-
from typing import Union
import struct

# ** Memory
mem = memoryview(bytearray(65536))

mem_rw = [False, True, True, True]

# Word access
wstruct = struct.Struct('<H')
# Signed byte access
signedbyte = struct.Struct('<b')


def pokew(addr: int, word):
    global mem
    if addr % 0x4000 == 0x3fff:
        if mem_rw[addr//0x4000]:
            mem[addr] = word % 256
        addr = (addr + 1) % 65536
        if mem_rw[addr//0x4000]:
            mem[addr] = word >> 8
    else:
        if mem_rw[addr//0x4000]:
            wstruct.pack_into(mem, addr, word)


def peekw(addr: int) -> int:
    global mem
    if addr == 65535:
        return (mem[65535] | (mem[0] << 8)) % 65536
    else:
        return wstruct.unpack_from(mem, addr)[0]


def pokeb(addr: int, byte):
    if mem_rw[addr//0x4000]:
        mem[addr] = byte


def peekb(addr: int) -> int:
    return mem[addr]


def peeksb(addr: int) -> int:
    return signedbyte.unpack_from(mem, addr)[0]
