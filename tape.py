# -*- coding: utf-8 -*-
import struct
import os
from enum import Enum



def sync_tape(tks: float):
    tks = tks / 280


def load(filename: str):
    global tap_filedata
    fdata = os.stat(filename)
    tap_filedata = memoryview(bytearray(fdata.st_size))
    with open(filename, 'rb') as f:
        f.readinto(tap_filedata)
    


tape_on = False
tap_filedata = None
tap_header_struct = struct.Struct('<c10sHHH')
tap_stage = TapeStage.TAPE_NONE
PILOTLEN = 2168
SYNC1LEN = 667
SYNC2LEN = 735
SIGN0LEN = 855
SIGN1LEN = 1710
SYNC3LEN = 954
FRAMEDOTS = 71680
SECDOTS = (FRAMEDOTS * 50)
MSDOTS = (FRAMEDOTS / 20)
HEADER_PDUR = 8063
HEADER_PAUSE = 500 * MSDOTS
BODY_PDUR = 3223
BODY_PAUSE = 1000 * MSDOTS


class TapeStage(Enum):
	TAPE_NONE = 0
	TAPE_PILOT = 1
	TAPE_SYNC1 = 2
	TAPE_SYNC2 = 3
	TAPE_SYNC3 = 4


"""
#define	PILOTLEN	2168
#define	SYNC1LEN	667
#define	SYNC2LEN	735
#define	SIGN0LEN	855
#define	SIGN1LEN	1710
#define	SYNC3LEN	954
#define	FRAMEDOTS	71680
#define SECDOTS		(FRAMEDOTS * 50)
#define	MSDOTS		(FRAMEDOTS / 20)

TapeBlock makeTapeBlock(unsigned char* ptr, int ln, int hd) {
	TapeBlock nblk;
	int i;
	int pause;
	unsigned char tmp;
	unsigned char crc;
	nblk.plen = PILOTLEN;
	nblk.s1len = SYNC1LEN;
	nblk.s2len = SYNC2LEN;
	nblk.len0 = SIGN0LEN;
	nblk.len1 = SIGN1LEN;
	nblk.breakPoint = 0;
	nblk.hasBytes = 1;
	nblk.isHeader = 0;
	nblk.sigCount = 0;
	nblk.data = NULL;
	if (hd) {
		nblk.pdur = 8063;
		pause = 500 * MSDOTS;
		nblk.isHeader = 1;
		crc = 0x00;
	} else {
		nblk.pdur = 3223;
		pause = 1000 * MSDOTS;
		crc = 0xff;
	}
	for (i=0; i < nblk.pdur; i++)
		blkAddPulse(&nblk,nblk.plen);
	if (nblk.s1len != 0)
		blkAddPulse(&nblk,nblk.s1len);
	if (nblk.s2len != 0)
		blkAddPulse(&nblk,nblk.s2len);
	nblk.dataPos = nblk.sigCount;
	blkAddByte(&nblk,crc,0,0);
	for (i=0; i < ln; i++) {
		tmp = *ptr;
		crc ^= tmp;
		blkAddByte(&nblk,tmp,0,0);
		ptr++;
	}
	blkAddByte(&nblk,crc,0,0);
	blkAddPulse(&nblk,SYNC3LEN);
	blkAddPulse(&nblk,pause);
	return nblk;
}

// add signal (1 level change)
void blkAddPulse(TapeBlock* blk, int len) {
	if ((blk->sigCount & 0xffff) == 0) {
		blk->data = realloc(blk->data,(blk->sigCount + 0x10000) * sizeof(TapeSignal));	// allocate mem for next 0x10000 signals
	}
	blk->data[blk->sigCount].size = len;
	blk->data[blk->sigCount].vol = blk->vol ? 0x60 : 0xa0;
	blk->vol ^= 1;
	blk->sigCount++;
}

// add pause. duration in ms
void blkAddPause(TapeBlock* blk, int len) {
	blkAddPulse(blk,len * MSDOTS * 2);
}

// add pulse (2 signals)
void blkAddWave(TapeBlock* blk, int len) {
	blkAddPulse(blk,len);
	blkAddPulse(blk,len);
}

// add byte. b0len/b1len = duration of 0/1 bits. When 0, it takes from block signals data
void blkAddByte(TapeBlock* blk, unsigned char data, int b0len, int b1len) {
	if (b0len == 0) b0len = blk->len0;
	if (b1len == 0) b1len = blk->len1;
	for (int msk = 0x80; msk > 0; msk >>= 1) {
		blkAddWave(blk, (data & msk) ? b1len : b0len);
	}
}
"""
