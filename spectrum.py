#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
ZX Spectrum Emulator
Vadim Kataev
www.technopedia.org

ver.0.1 2005
ver.0.2 June 2008
Python 3 conversion + modifications by CityAceE 2018
Full z80 core rewrite + optimizations + improvements Q-Master 2019
Simple fixes Bedazzle 2020
'''

import sys
import Z80
import video
import load


ROMFILE = '48.rom'


def load_rom(romfilename):
    ''' Load given romfile into memory '''

    with open(romfilename, 'rb') as rom:
        rom.readinto(Z80.memory.mem)

    print('Loaded ROM: %s' % romfilename)


def run():
    ''' Start the execution '''
    try:
        Z80.execute()
    except KeyboardInterrupt:
        return


video.init()
Z80.Z80(3.5)  # MhZ

load_rom(ROMFILE)
Z80.reset()
Z80.ports.port_out(254, 0xff)  # white border on startup

sys.setswitchinterval(255)  # we don't use threads, kind of speed up


SNADIR = '../Perfect_SNA/'

# ok
# load.load_sna(SNADIR + 'Action Reflex.sna')
# load.load_sna(SNADIR + 'Ball Breaker 1.sna')
# load.load_sna(SNADIR + 'Ball Breaker 2.sna')
# load.load_sna(SNADIR + 'Batty.sna')
# load.load_sna(SNADIR + 'Bomb Jack.sna')
# load.load_sna(SNADIR + 'Bruce Lee.sna')
# load.load_sna(SNADIR + 'Capitan Trueno 1.sna')
# load.load_sna(SNADIR + 'Cybernoid 1.sna')
# load.load_sna(SNADIR + 'Cybernoid 2.sna')
# load.load_sna(SNADIR + 'Cyclone.sna')
# load.load_sna(SNADIR + 'Eric And The Floaters.sna')
# load.load_sna(SNADIR + 'Exolon.sna')
# load.load_sna(SNADIR + 'Freddy Hardest 1.sna')
# load.load_sna(SNADIR + 'Frost Byte.sna')
# load.load_sna(SNADIR + 'Head Over Heels.sna')
# load.load_sna(SNADIR + 'Heavy On The Magick (Rebound).sna')
# load.load_sna(SNADIR + 'Legions Of Death.sna')
# load.load_sna(SNADIR + 'Lord Of The Rings (Part 1).sna')
# load.load_sna(SNADIR + 'Mermaid Madness.sna')
# load.load_sna(SNADIR + 'Monty On The Run.sna')
# load.load_sna(SNADIR + 'Movie.sna')
# load.load_sna(SNADIR + 'Nebulus.sna')
# load.load_sna(SNADIR + 'Penetrator.sna')
# load.load_sna(SNADIR + 'Rick Dangerous.sna')
# load.load_sna(SNADIR + 'Ruff and Reddy.sna')
# load.load_sna(SNADIR + 'Saboteur 1.sna')
# load.load_sna(SNADIR + 'Saboteur 2.sna')
# load.load_sna(SNADIR + 'Scuba Dive.sna')
# load.load_sna(SNADIR + 'Three Weeks In Paradise.sna')
load.load_sna(SNADIR + 'Mask_3_Venom_strikes_back.sna')
# load.load_sna(SNADIR + 'Yogi Bear.sna')
# load.load_sna(SNADIR + 'Zynaps.sna')

# invalid
# load.load_sna(SNADIR + 'Arkanoid 2.sna')       # vanishing bat
# load.load_sna(SNADIR + 'Batman.sna')           # blinking sprites
# load.load_sna(SNADIR + 'Dizzy7.sna')           # vanishing sprite
# load.load_sna(SNADIR + 'Puzznic.sna')          # no cursor
# load.load_sna(SNADIR + 'Ramparts.sna')         # tape error
# load.load_sna(SNADIR + 'Storm Lord.sna')       # blinking sprites

# load.load_sna(SNADIR + 'bt_city.sna')
# load.load_sna(SNADIR + 'bt.sna')
# load.load_sna(SNADIR + 'z80full_with_pause.SNA')
run()
