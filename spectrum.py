#!/usr/bin/env python3
# ZX Spectrum Emulator
# Vadim Kataev
# www.technopedia.org
#
# ver.0.1 2005
# ver.0.2 June 2008
# Python 3 conversion + modifications by CityAceE 2018

import sys

import Z80
import video
import load

romfile = '48.rom'


def load_rom(romfilename):
    with open(romfilename, 'rb') as rom:
        rom.readinto(Z80.mem)
    print('Loaded ROM: %s' % romfilename)


def run():
    try:
        Z80.execute()
    except KeyboardInterrupt:
        return


video.init()
Z80.Z80(3.5)  # MhZ

load_rom(romfile)
Z80.reset()
Z80.outb(254, 0xff)  # white border on startup

sys.setcheckinterval(255)  # we don't use threads, kind of speed up

#load.load_z80('./games/Batty.z80')
load.load_sna('./games/Exolon.sna')

run()
