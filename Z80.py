import struct
import video
import memory
import ports

show_debug_info = False
tstatesPerInterrupt = 0

def Z80(clockFrequencyInMHz):
    global tstatesPerInterrupt
    # 50Hz for main interrupt signal
    tstatesPerInterrupt = int((clockFrequencyInMHz * 1e6) / 50)


IM0 = 0
IM1 = 1
IM2 = 2

F_C = 0x01
F_N = 0x02
F_PV = 0x04
F_3 = 0x08
F_H = 0x10
F_5 = 0x20
F_Z = 0x40
F_S = 0x80
F_3_16 = F_3 << 8
F_5_16 = F_5 << 8

PF = F_PV
p_ = 0


parity = [False] * 256
for i in range(256):
    p = True
    int_type = i
    while (int_type):
        p = not p_
        int_type = int_type & (int_type - 1)
    parity[i] = p


# **Main registers
_AF_b = bytearray(2)
_A_F = memoryview(_AF_b)
_F = _A_F[0:1]
_A = _A_F[1:2]
_AF = _A_F.cast('H')
_fS = False
_fZ = False
_f5 = False
_fH = False
_f3 = False
_fPV = False
_fN = False
_fC = False


def setflags():
    global _f3, _f5, _fC, _fH, _fN, _fPV, _fS, _fZ
    _fS = (_F[0] & F_S) != 0
    _fZ = (_F[0] & F_Z) != 0
    _f5 = (_F[0] & F_5) != 0
    _fH = (_F[0] & F_H) != 0
    _f3 = (_F[0] & F_3) != 0
    _fPV = (_F[0] & F_PV) != 0
    _fN = (_F[0] & F_N) != 0
    _fC = (_F[0] & F_C) != 0


_HL_b = bytearray(2)
_H_L = memoryview(_HL_b)
_L = _H_L[0:1]
_H = _H_L[1:2]
_HL = _H_L.cast('H')

_BC_b = bytearray(2)
_B_C = memoryview(_BC_b)
_C = _B_C[0:1]
_B = _B_C[1:2]
_BC = _B_C.cast('H')

_DE_b = bytearray(2)
_D_E = memoryview(_DE_b)
_E = _D_E[0:1]
_D = _D_E[1:2]
_DE = _D_E.cast('H')


# ** Alternate registers
_AF_b_ = bytearray(2)
_A_F_ = memoryview(_AF_b_)
_F_ = _A_F_[0:1]
_A_ = _A_F_[1:2]
_AF_ = _A_F_.cast('H')

_HL_b_ = bytearray(2)
_H_L_ = memoryview(_HL_b_)
_L_ = _H_L_[0:1]
_H_ = _H_L_[1:2]
_HL_ = _H_L_.cast('H')

_BC_b_ = bytearray(2)
_B_C_ = memoryview(_BC_b_)
_C_ = _B_C_[0:1]
_B_ = _B_C_[1:2]
_BC_ = _B_C_.cast('H')

_DE_b_ = bytearray(2)
_D_E_ = memoryview(_DE_b_)
_E_ = _D_E_[0:1]
_D_ = _D_E_[1:2]
_DE_ = _D_E_.cast('H')


# ** Index registers - ID used as temporary for ix/iy
_IX_b = bytearray(2)
_IXH_IXL = memoryview(_IX_b)
_IXL = _IXH_IXL[0:1]
_IXH = _IXH_IXL[1:2]
_IX = _IXH_IXL.cast('H')

_IY_b = bytearray(2)
_IYH_IYL = memoryview(_IY_b)
_IYL = _IYH_IYL[0:1]
_IYH = _IYH_IYL[1:2]
_IY = _IYH_IYL.cast('H')

_IDH = None
_IDL = None
_ID = None


# ** Stack Pointer and Program Counter
_SP_b = bytearray(2)
_SP = memoryview(_SP_b).cast('H')

_PC_b = bytearray(2)
_PC = memoryview(_PC_b).cast('H')


# ** Interrupt and Refresh registers
_I_b = bytearray(2)
_IH_IL = memoryview(_I_b)
_I = _IH_IL[1:2]
_Ifull = _IH_IL.cast('H')


# Memory refresh register
_R_b = _IH_IL[0:1]
_R7_b = 0


def _Rget():
    global _R7_b
    return _R_b[0]


def _Rset(r):
    global _R7_b
    _R_b[0] = r
    _R7_b = 0x80 if r > 0x7F else 0
_R = property(_Rget, _Rset)


def inc_r(r = 1):
    global _R7_b
    _R_b[0] = ((_R_b[0] + r) % 128) + _R7_b


# ** Interrupt flip-flops
_IFF1 = True
_IFF2 = True
_IM = IM2


# Stack access
def pushw(word):
    global _SP
    _SP[0] = (_SP[0] - 2) % 65536
    memory.pokew(_SP[0], word)


def popw():
    t = memory.peekw(_SP[0])
    _SP[0] = (_SP[0] + 2) % 65536
    return t


# Call stack
def pushpc():
    pushw(_PC[0])


def poppc():
    _PC[0] = popw()


def nxtpcb():
    t = memory.peekb(_PC[0])
    _PC[0] = (_PC[0] + 1) % 65536
    return t


def nxtpcsb():
    global show_debug_info
    t = memory.peeksb(_PC[0])
    _PC[0] = (_PC[0] + 1) % 65536
    if show_debug_info:
        print(f'signedbyte: {t}, PC: 0x{_PC[0]:4x}')
    return t


def incpcsb():
    t = nxtpcsb()
    _PC[0] = (_PC[0] + t) % 65536


def nxtpcw():
    t = memory.peekw(_PC[0])
    _PC[0] = (_PC[0] + 2) % 65536
    return t


# Reset all registers to power on state
def reset():
    global _R, _IFF1, _IFF2
    global _fS, _fZ, _f5, _fH, _f3, _fPV, _fN, _fC
    _PC[0] = 0
    _SP[0] = 0

    _fS = False
    _fZ = False
    _f5 = False
    _fH = False
    _f3 = False
    _fPV = False
    _fN = False
    _fC = False
    _AF[0] = 0
    _BC[0] = 0
    _DE[0] = 0
    _HL[0] = 0

    _AF_[0] = 0
    _BC_[0] = 0
    _DE_[0] = 0
    _HL_[0] = 0

    _IX[0] = 0
    _IY[0] = 0
    _R = 0
    _Ifull[0] = 0
    _IFF1 = 0
    _IFF2 = 0
    _IM = IM0


def show_registers():
    global show_debug_info
    if show_debug_info:
        print(f'PC: 0x{_PC[0]:04x}\tOPCODE: {memory.peekb(_PC[0]):03d}\tA: 0x{_A[0]:02x}\tHL: 0x{_HL[0]:04x}\tBC: 0x{_BC[0]:04x}\tDE: 0x{_DE[0]:04x}')
        print(f'FLAGS 0x{_F[0]:02x}\tC: {_fC}\tN: {_fN}\tPV: {_fPV}\t3: {_f3}\tH: {_fH}\t5: {_f5}\tZ: {_fZ}\tS: {_fS}')
        print(f'IFF1 {_IFF1}, IFF2 {_IFF2}')


# Interrupt handlers
# def interruptTriggered( tstates ):
#		return (tstates >= 0);


video_update_time = 0


def interrupt():
    global video_update_time
    Hz = 25

    video_update_time += 1
    ports.keyboard.do_keys()
    if not (video_update_time % int(50 / Hz)):
        video.update()
    return interruptCPU()


def interruptCPU():
    global _IM, _IFF1, show_debug_info
    # If not a non-maskable interrupt
    def im0im1():
        global _IFF1, _IFF2
        pushpc()
        _IFF1 = False
        _IFF2 = False
        _PC[0] = 56
        return 13

    def im2():
        global _IFF1, _IFF2
        pushpc()
        _IFF1 = False
        _IFF2 = False
        _PC[0] = memory.peekw(_Ifull[0])
        return 19

    if not _IFF1:
        #if show_debug_info:
        #    print('NO interrupt')
        return 0
    if show_debug_info:
        print(f'Interrupt: {_IM}, PC: 0x{_PC[0]:4x}, IFF1: {_IFF1}')
    return {IM0: im0im1, IM1: im0im1, IM2: im2}.get(_IM)()


# Z80 fetch/execute loop
local_tstates = -tstatesPerInterrupt  # -70000
def check_tstates():
    global local_tstates
    if local_tstates >= 0:
        #print(f'LTS: {local_tstates} _PC: {_PC[0]:4x}')
        local_tstates -= tstatesPerInterrupt - interrupt()


def execute():
    global _R, main_cmds, local_tstates

    while True:
        check_tstates()
        inc_r()
        show_registers()
        opcode = nxtpcb()
        if opcode == 118:  # HALT
            haltsToInterrupt = int(((-local_tstates - 1) / 4) + 1)
            local_tstates += (haltsToInterrupt * 4)
            inc_r(haltsToInterrupt - 1)
            continue
        else:
            local_tstates += main_cmds.get(opcode)()


def execute_id():
    global _ixiydict
    inc_r()
    opcode = nxtpcb()
    return _ixiydict.get(opcode, nop)()


def execute_id_cb(opcode, z):
    global _idcbdict
    return _idcbdict.get(opcode)(z)


def nop():
    return 4


# EXX
def exx():
    global _HL, _HL_, _H, _H_, _L, _L_
    global _DE, _DE_, _D, _D_, _E, _E_
    global _BC, _BC_, _B, _B_, _C, _C_
    _HL, _HL_ = _HL_, _HL
    _H, _H_ = _H_, _H
    _L, _L_ = _L_, _L

    _DE, _DE_ = _DE_, _DE
    _D, _D_ = _D_, _D
    _E, _E_ = _E_, _E

    _BC, _BC_ = _BC_, _BC
    _B, _B_ = _B_, _B
    _C, _C_ = _C_, _C
    return 4


# EX AF,AF'
def ex_af_af():
    global _AF, _AF_, _A, _A_, _F, _F_
    _F[0] = (F_S if _fS else 0) + \
        (F_Z if _fZ else 0) + \
        (F_5 if _f5 else 0) + \
        (F_H if _fH else 0) + \
        (F_3 if _f3 else 0) + \
        (F_PV if _fPV else 0) + \
        (F_N if _fN else 0) + \
        (F_C if _fC else 0)
    _AF, _AF_ = _AF_, _AF
    _A, _A_ = _A_, _A
    _F, _F_ = _F_, _F
    setflags()
    return 4


def djnz():
    _B[0] = qdec8(_B[0])
    if _B[0] != 0:
        incpcsb()
        return 13
    else:
        _PC[0] = inc16(_PC[0])
        return 8


def jr():
    incpcsb()
    return 12


def jrnz():
    global _fZ
    if not _fZ:
        incpcsb()
        return 12
    else:
        _PC[0] = inc16(_PC[0])
        return 7


def jrz():
    global _fZ
    if _fZ:
        incpcsb()
        return 12
    else:
        _PC[0] = inc16(_PC[0])
        return 7


def jrnc():
    global _fC
    if not _fC:
        incpcsb()
        return 12
    else:
        _PC[0] = inc16(_PC[0])
        return 7


def jrc():
    global _fC
    if _fC:
        incpcsb()
        return 12
    else:
        _PC[0] = inc16(_PC[0])
        return 7


# LD rr,nn / ADD HL,rr
def ldbcnn():
    _BC[0] = nxtpcw()
    return 10


def addhlbc():
    _HL[0] = add16(_HL[0], _BC[0])
    return 11


def lddenn():
    _DE[0] = nxtpcw()
    return 10


def addhlde():
    _HL[0] = add16(_HL[0], _DE[0])
    return 11


def ldhlnn():
    _HL[0] = nxtpcw()
    return 10


def addhlhl():
    hl = _HL[0]
    _HL[0] = add16(hl, hl)
    return 11


def ldspnn():
    _SP[0] = nxtpcw()
    return 10


def addhlsp():
    _HL[0] = add16(_HL[0], _SP[0])
    return 11


# LD (**),A/A,(**)
def ldtobca():
    memory.pokeb(_BC[0], _A[0])
    return 7


def ldafrombc():
    _A[0] = memory.peekb(_BC[0])
    return 7


def ldtodea():
    memory.pokeb(_DE[0], _A[0])
    return 7


def ldafromde():
    _A[0] = memory.peekb(_DE[0])
    return 7

def ldtonnhl():
    memory.pokew(nxtpcw(), _HL[0])
    return 16


def ldhlfromnn():
    _HL[0] = memory.peekw(nxtpcw())
    return 16


def ldtonna():
    memory.pokeb(nxtpcw(), _A[0])
    return 13


def ldafromnn():
    _A[0] = memory.peekb(nxtpcw())
    return 13


# INC/DEC *
def incbc():
    _BC[0] = inc16(_BC[0])
    return 6


def decbc():
    _BC[0] = dec16(_BC[0])
    return 6


def incde():
    _DE[0] = inc16(_DE[0])
    return 6


def decde():
    _DE[0] = dec16(_DE[0])
    return 6


def inchl():
    _HL[0] = inc16(_HL[0])
    return 6


def dechl():
    _HL[0] = dec16(_HL[0])
    return 6


def incsp():
    _SP[0] = inc16(_SP[0])
    return 6


def decsp():
    _SP[0] = dec16(_SP[0])
    return 6


# INC *
def incb():
    _B[0] = inc8(_B[0])
    return 4


def incc():
    _C[0] = inc8(_C[0])
    return 4


def incd():
    _D[0] = inc8(_D[0])
    return 4


def ince():
    _E[0] = inc8(_E[0])
    return 4


def inch():
    _H[0] = inc8(_H[0])
    return 4


def incl():
    _L[0] = inc8(_L[0])
    return 4


def incinhl():
    memory.pokeb(_HL[0], inc8(memory.peekb(_HL[0])))
    return 11


def inca():
    _A[0] = inc8(_A[0])
    return 4


# DEC *
def decb():
    _B[0] = dec8(_B[0])
    return 4


def decc():
    _C[0] = dec8(_C[0])
    return 4


def decd():
    _D[0] = dec8(_D[0])
    return 4


def dece():
    _E[0] = dec8(_E[0])
    return 4


def dech():
    _H[0] = dec8(_H[0])
    return 4


def decl():
    _L[0] = dec8(_L[0])
    return 4


def decinhl():
    memory.pokeb(_HL[0], dec8(memory.peekb(_HL[0])))
    return 11


def deca():
    _A[0] = dec8(_A[0])
    return 4


# LD *,N
def ldbn():
    _B[0] = nxtpcb()
    return 7


def ldcn():
    _C[0] = nxtpcb()
    return 7


def lddn():
    _D[0] = nxtpcb()
    return 7


def lden():
    _E[0] = nxtpcb()
    return 7


def ldhn():
    _H[0] = nxtpcb()
    return 7


def ldln():
    _L[0] = nxtpcb()
    return 7


def ldtohln():
    memory.pokeb(_HL[0], nxtpcb())
    return 10


def ldan():
    _A[0] = nxtpcb()
    return 7


# R**A
def rlca():
    global _f3, _f5, _fN, _fH, _fC
    ans = _A[0]
    c = ans > 0x7f
    ans = ((ans << 1) + (0x01 if c else 0)) % 256
    _f3 = (ans & F_3) != 0
    _f5 = (ans & F_5) != 0
    _fN = False
    _fH = False
    _fC = c
    _A[0] = ans
    return 4


# Rotate Left through Carry - alters H N C 3 5 flags (CHECKED)
def rla():
    global _f3, _f5, _fN, _fH, _fC
    ans = _A[0]
    c = ans > 0x7F
    ans = ((ans << 1) + (1 if _fC else 0)) % 256
    _f3 = (ans & F_3) != 0
    _f5 = (ans & F_5) != 0
    _fN = False
    _fH = False
    _fC = c
    _A[0] = ans
    return 4


# Rotate Right - alters H N C 3 5 flags (CHECKED)
def rrca():
    global _f3, _f5, _fN, _fH, _fC
    ans = _A[0]
    c = (ans % 2) != 0
    ans = ((ans >> 1) + (0x80 if c else 0)) % 256
    _f3 = (ans & F_3) != 0
    _f5 = (ans & F_5) != 0
    _fN = False
    _fH = False
    _fC = c
    _A[0] = ans
    return 4


# Rotate Right through Carry - alters H N C 3 5 flags (CHECKED)
def rra():
    global _f3, _f5, _fN, _fH, _fC
    ans = _A[0]
    c = (ans % 2) != 0
    ans = ((ans >> 1) + (0x80 if _fC else 0)) % 256
    _f3 = (ans & F_3) != 0
    _f5 = (ans & F_5) != 0
    _fN = False
    _fH = False
    _fC = c
    _A[0] = ans
    return 4


# Decimal Adjust Accumulator - alters all flags (CHECKED)
def daa():
    global _fC, _fN, _fPV, _fH
    ans = _A[0]
    incr = 0
    carry = _fC

    if _fH or ((ans % 16) > 0x09):
        incr |= 0x06

    if carry or (ans > 0x9f) or ((ans > 0x8f) and ((ans % 16) > 0x09)):
        incr |= 0x60

    if ans > 0x99:
        carry = True

    if _fN:
        sub_a(incr)
    else:
        add_a(incr)

    ans = _A[0]
    _fC = carry
    _fPV = parity[ans]
    return 4


# One's complement - alters N H 3 5 flags (CHECKED)
def cpla():
    global _f3, _f5, _fH, _fN
    ans = _A[0] ^ 0xff
    _f3 = (ans & F_3) != 0
    _f5 = (ans & F_5) != 0
    _fH = True
    _fN = True
    _A[0] = ans
    return 4


# Set carry flag - alters N H 3 5 C flags (CHECKED)
def scf():
    global _f3, _f5, _fH, _fN, _fC
    ans = _A[0]
    _f3 = (ans & F_3) != 0
    _f5 = (ans & F_5) != 0
    _fN = False
    _fH = False
    _fC = True
    return 4


# Complement carry flag - alters N 3 5 C flags (CHECKED)
def ccf():
    global _f3, _f5, _fN, _fC, _fH
    ans = _A[0]
    _f3 = (ans & F_3) != 0
    _f5 = (ans & F_5) != 0
    _fH = _fC
    _fC = not _fC
    _fN = False
    return 4


# LD B,*
def ldbb():
    return 4


def ldbc():
    _B[0] = _C[0]
    return 4


def ldbd():
    _B[0] = _D[0]
    return 4


def ldbe():
    _B[0] = _E[0]
    return 4


def ldbh():
    _B[0] = _H[0]
    return 4


def ldbl():
    _B[0] = _L[0]
    return 4


def ldbfromhl():
    _B[0] = memory.peekb(_HL[0])
    return 7


def ldba():
    _B[0] = _A[0]
    return 4


# LD C,*
def ldcb():
    _C[0] = _B[0]
    return 4


def ldcc():
    return 4


def ldcd():
    _C[0] = _D[0]
    return 4


def ldce():
    _C[0] = _E[0]
    return 4


def ldch():
    _C[0] = _H[0]
    return 4


def ldcl():
    _C[0] = _L[0]
    return 4


def ldcfromhl():
    _C[0] = memory.peekb(_HL[0])
    return 7


def ldca():
    _C[0] = _A[0]
    return 4


# LD D,*
def lddb():
    _D[0] = _B[0]
    return 4


def lddc():
    _D[0] = _C[0]
    return 4


def lddd():
    return 4


def ldde():
    _D[0] = _E[0]
    return 4


def lddh():
    _D[0] = _H[0]
    return 4


def lddl():
    _D[0] = _L[0]
    return 4


def lddfromhl():
    _D[0] = memory.peekb(_HL[0])
    return 7


def ldda():
    _D[0] = _A[0]
    return 4


# LD E,*
def ldeb():
    _E[0] = _B[0]
    return 4


def ldec():
    _E[0] = _C[0]
    return 4


def lded():
    _E[0] = _D[0]
    return 4


def ldee():
    return 4


def ldeh():
    _E[0] = _H[0]
    return 4


def ldel():
    _E[0] = _L[0]
    return 4


def ldefromhl():
    _E[0] = memory.peekb(_HL[0])
    return 7


def ldea():
    _E[0] = _A[0]
    return 4


# LD H,*
def ldhb():
    _H[0] = _B[0]
    return 4


def ldhc():
    _H[0] = _C[0]
    return 4


def ldhd():
    _H[0] = _D[0]
    return 4


def ldhe():
    _H[0] = _E[0]
    return 4


def ldhh():
    return 4


def ldhl():
    _H[0] = _L[0]
    return 4


def ldhfromhl():
    _H[0] = memory.peekb(_HL[0])
    return 7


def ldha():
    _H[0] = _A[0]
    return 4


# LD L,*
def ldlb():
    _L[0] = _B[0]
    return 4


def ldlc():
    _L[0] = _C[0]
    return 4


def ldld():
    _L[0] = _D[0]
    return 4


def ldle():
    _L[0] = _E[0]
    return 4


def ldlh():
    _L[0] = _H[0]
    return 4


def ldll():
    return 4


def ldlfromhl():
    _L[0] = memory.peekb(_HL[0])
    return 7


def ldla():
    _L[0] = _A[0]
    return 4


# LD (HL),*
def ldtohlb():
    memory.pokeb(_HL[0], _B[0])
    return 7


def ldtohlc():
    memory.pokeb(_HL[0], _C[0])
    return 7


def ldtohld():
    memory.pokeb(_HL[0], _D[0])
    return 7


def ldtohle():
    memory.pokeb(_HL[0], _E[0])
    return 7


def ldtohlh():
    memory.pokeb(_HL[0], _H[0])
    return 7


def ldtohll():
    memory.pokeb(_HL[0], _L[0])
    return 7


def ldtohla():
    memory.pokeb(_HL[0], _A[0])
    return 7


# LD A,*
def ldab():
    _A[0] = _B[0]
    return 4


def ldac():
    _A[0] = _C[0]
    return 4


def ldad():
    _A[0] = _D[0]
    return 4


def ldae():
    _A[0] = _E[0]
    return 4


def ldah():
    _A[0] = _H[0]
    return 4


def ldal():
    _A[0] = _L[0]
    return 4


def ldafromhl():
    _A[0] = memory.peekb(_HL[0])
    return 7


def ldaa():
    return 4


# ADD A,*
def addab():
    add_a(_B[0])
    return 4


def addac():
    add_a(_C[0])
    return 4


def addad():
    add_a(_D[0])
    return 4


def addae():
    add_a(_E[0])
    return 4


def addah():
    add_a(_H[0])
    return 4


def addal():
    add_a(_L[0])
    return 4


def addafromhl():
    add_a(memory.peekb(_HL[0]))
    return 7


def addaa():
    add_a(_A[0])
    return 4


# ADC A,*
def adcab():
    adc_a(_B[0])
    return 4


def adcac():
    adc_a(_C[0])
    return 4


def adcad():
    adc_a(_D[0])
    return 4


def adcae():
    adc_a(_E[0])
    return 4


def adcah():
    adc_a(_H[0])
    return 4


def adcal():
    adc_a(_L[0])
    return 4


def adcafromhl():
    adc_a(memory.peekb(_HL[0]))
    return 7


def adcaa():
    adc_a(_A[0])
    return 4


# SUB A,*
def subab():
    sub_a(_B[0])
    return 4


def subac():
    sub_a(_C[0])
    return 4


def subad():
    sub_a(_D[0])
    return 4


def subae():
    sub_a(_E[0])
    return 4


def subah():
    sub_a(_H[0])
    return 4


def subal():
    sub_a(_L[0])
    return 4


def subafromhl():
    sub_a(memory.peekb(_HL[0]))
    return 7


def subaa():
    sub_a(_A[0])
    return 4


# SBC A,*
def sbcab():
    sbc_a(_B[0])
    return 4


def sbcac():
    sbc_a(_C[0])
    return 4


def sbcad():
    sbc_a(_D[0])
    return 4


def sbcae():
    sbc_a(_E[0])
    return 4


def sbcah():
    sbc_a(_H[0])
    return 4


def sbcal():
    sbc_a(_L[0])
    return 4


def sbcafromhl():
    sbc_a(memory.peekb(_HL[0]))
    return 7


def sbcaa():
    sbc_a(_A[0])
    return 4


# AND A,*
def andab():
    and_a(_B[0])
    return 4


def andac():
    and_a(_C[0])
    return 4


def andad():
    and_a(_D[0])
    return 4


def andae():
    and_a(_E[0])
    return 4


def andah():
    and_a(_H[0])
    return 4


def andal():
    and_a(_L[0])
    return 4


def andafromhl():
    and_a(memory.peekb(_HL[0]))
    return 7


def andaa():
    and_a(_A[0])
    return 4


# XOR A,*
def xorab():
    xor_a(_B[0])
    return 4


def xorac():
    xor_a(_C[0])
    return 4


def xorad():
    xor_a(_D[0])
    return 4


def xorae():
    xor_a(_E[0])
    return 4


def xorah():
    xor_a(_H[0])
    return 4


def xoral():
    xor_a(_L[0])
    return 4


def xorafromhl():
    xor_a(memory.peekb(_HL[0]))
    return 7


def xoraa():
    xor_a(_A[0])
    return 4


# OR A,*
def orab():
    or_a(_B[0])
    return 4


def orac():
    or_a(_C[0])
    return 4


def orad():
    or_a(_D[0])
    return 4


def orae():
    or_a(_E[0])
    return 4


def orah():
    or_a(_H[0])
    return 4


def oral():
    or_a(_L[0])
    return 4


def orafromhl():
    or_a(memory.peekb(_HL[0]))
    return 7


def oraa():
    or_a(_A[0])
    return 4


# CP A,*
def cpab():
    cp_a(_B[0])
    return 4


def cpac():
    cp_a(_C[0])
    return 4


def cpad():
    cp_a(_D[0])
    return 4


def cpae():
    cp_a(_E[0])
    return 4


def cpah():
    cp_a(_H[0])
    return 4


def cpal():
    cp_a(_L[0])
    return 4


def cpafromhl():
    cp_a(memory.peekb(_HL[0]))
    return 7


def cpaa():
    cp_a(_A[0])
    return 4


# RET cc
def retnz():
    global _fZ
    if not _fZ:
        poppc()
        return 11
    else:
        return 5

def retz():
    global _fZ
    if _fZ:
        poppc()
        return 11
    else:
        return 5


def retnc():
    global _fC
    if not _fC:
        poppc()
        return 11
    else:
        return 5


def retc():
    global _fC
    if _fC:
        poppc()
        return 11
    else:
        return 5


def retpo():
    global _fPV
    if not _fPV:
        poppc()
        return 11
    else:
        return 5


def retpe():
    global _fPV
    if _fPV:
        poppc()
        return 11
    else:
        return 5


def retp():
    global _fS
    if not _fS:
        poppc()
        return 11
    else:
        return 5


def retm():
    global _fS
    if _fS:
        poppc()
        return 11
    else:
        return 5


# POP
def popbc():
    _BC[0] = popw()
    return 10


def popde():
    _DE[0] = popw()
    return 10


def pophl():
    _HL[0] = popw()
    return 10


def popaf():
    _AF[0] = popw()
    setflags()
    return 10


# JP cc,nn
def jpnznn():
    global _fZ
    if not _fZ:
        _PC[0] = nxtpcw()
    else:
        _PC[0] = (_PC[0] + 2) % 65536
    return 10


def jpznn():
    global _fZ
    if _fZ:
        _PC[0] = nxtpcw()
    else:
        _PC[0] = (_PC[0] + 2) % 65536
    return 10


def jpncnn():
    global _fC
    if not _fC:
        _PC[0] = nxtpcw()
    else:
        _PC[0] = (_PC[0] + 2) % 65536
    return 10


def jpcnn():
    global _fC
    if _fC:
        _PC[0] = nxtpcw()
    else:
        _PC[0] = (_PC[0] + 2) % 65536
    return 10


def jpponn():
    global _fPV
    if not _fPV:
        _PC[0] = nxtpcw()
    else:
        _PC[0] = (_PC[0] + 2) % 65536
    return 10


def jppenn():
    global _fPV
    if _fPV:
        _PC[0] = nxtpcw()
    else:
        _PC[0] = (_PC[0] + 2) % 65536
    return 10


def jppnn():
    global _fS
    if not _fS:
        _PC[0] = nxtpcw()
    else:
        _PC[0] = (_PC[0] + 2) % 65536
    return 10


def jpmnn():
    global _fS
    if _fS:
        _PC[0] = nxtpcw()
    else:
        _PC[0] = (_PC[0] + 2) % 65536
    return 10


# Various
def jphl():
    _PC[0] = _HL[0]
    return 4


def ldsphl():
    _SP[0] = _HL[0]
    return 6


def ret():
    poppc()
    return 10


def jpnn():
    _PC[0] = nxtpcw()
    return 10


# CB prefix
#RLC *
def rlcb():
    _B[0] = rlc(_B[0])
    return 8


def rlcc():
    _C[0] = rlc(_C[0])
    return 8


def rlcd():
    _D[0] = rlc(_D[0])
    return 8


def rlce():
    _E[0] = rlc(_E[0])
    return 8


def rlch():
    _H[0] = rlc(_H[0])
    return 8


def rlcl():
    _L[0] = rlc(_L[0])
    return 8


def rlcfromhl():
    memory.pokeb(_HL[0], rlc(memory.peekb(_HL[0])))
    return 15


def rlc_a():
    _A[0] = rlc(_A[0])
    return 8


#RRC *
def rrcb():
    _B[0] = rrc(_B[0])
    return 8


def rrcc():
    _C[0] = rrc(_C[0])
    return 8


def rrcd():
    _D[0] = rrc(_D[0])
    return 8


def rrce():
    _E[0] = rrc(_E[0])
    return 8


def rrch():
    _H[0] = rrc(_H[0])
    return 8


def rrcl():
    _L[0] = rrc(_L[0])
    return 8


def rrcfromhl():
    memory.pokeb(_HL[0], rrc(memory.peekb(_HL[0])))
    return 15


def rrc_a():
    _A[0] = rrc(_A[0])
    return 8


#RL *
def rlb():
    _B[0] = rl(_B[0])
    return 8


def rl_c():
    _C[0] = rl(_C[0])
    return 8


def rld():
    _D[0] = rl(_D[0])
    return 8


def rle():
    _E[0] = rl(_E[0])
    return 8


def rlh():
    _H[0] = rl(_H[0])
    return 8


def rll():
    _L[0] = rl(_L[0])
    return 8


def rlfromhl():
    memory.pokeb(_HL[0], rl(memory.peekb(_HL[0])))
    return 15


def rl_a():
    _A[0] = rl(_A[0])
    return 8


# RR *
def rrb():
    _B[0] = rr(_B[0])
    return 8


def rr_c():
    _C[0] = rr(_C[0])
    return 8


def rrd():
    _D[0] = rr(_D[0])
    return 8


def rre():
    _E[0] = rr(_E[0])
    return 8


def rrh():
    _H[0] = rr(_H[0])
    return 8


def rrl():
    _L[0] = rr(_L[0])
    return 8


def rrfromhl():
    memory.pokeb(_HL[0], rr(memory.peekb(_HL[0])))
    return 15


def rr_a():
    _A[0] = rr(_A[0])
    return 8


# SLA *
def slab():
    _B[0] = sla(_B[0])
    return 8


def slac():
    _C[0] = sla(_C[0])
    return 8


def slad():
    _D[0] = sla(_D[0])
    return 8


def slae():
    _E[0] = sla(_E[0])
    return 8


def slah():
    _H[0] = sla(_H[0])
    return 8


def slal():
    _L[0] = sla(_L[0])
    return 8


def slafromhl():
    memory.pokeb(_HL[0], sla(memory.peekb(_HL[0])))
    return 15


def sla_a():
    _A[0] = sla(_A[0])
    return 8


# SRA *
def srab():
    _B[0] = sra(_B[0])
    return 8


def srac():
    _C[0] = sra(_C[0])
    return 8


def srad():
    _D[0] = sra(_D[0])
    return 8


def srae():
    _E[0] = sra(_E[0])
    return 8


def srah():
    _H[0] = sra(_H[0])
    return 8


def sral():
    _L[0] = sra(_L[0])
    return 8


def srafromhl():
    memory.pokeb(_HL[0], sra(memory.peekb(_HL[0])))
    return 15


def sra_a():
    _A[0] = sra(_A[0])
    return 8


# SLS *
def slsb():
    _B[0] = sls(_B[0])
    return 8


def slsc():
    _C[0] = sls(_C[0])
    return 8


def slsd():
    _D[0] = sls(_D[0])
    return 8


def slse():
    _E[0] = sls(_E[0])
    return 8


def slsh():
    _H[0] = sls(_H[0])
    return 8


def slsl():
    _L[0] = sls(_L[0])
    return 8


def slsfromhl():
    memory.pokeb(_HL[0], sls(memory.peekb(_HL[0])))
    return 15


def sls_a():
    _A[0] = sls(_A[0])
    return 8


# SRL *
def srlb():
    _B[0] = srl(_B[0])
    return 8


def srlc():
    _C[0] = srl(_C[0])
    return 8


def srld():
    _D[0] = srl(_D[0])
    return 8


def srle():
    _E[0] = srl(_E[0])
    return 8


def srlh():
    _H[0] = srl(_H[0])
    return 8


def srll():
    _L[0] = srl(_L[0])
    return 8


def srlfromhl():
    memory.pokeb(_HL[0], srl(memory.peekb(_HL[0])))
    return 15


def srl_a():
    _A[0] = srl(_A[0])
    return 8


# BIT 0, *
def bit0b():
    bit(0x01, _B[0])
    return 8


def bit0c():
    bit(0x01, _C[0])
    return 8


def bit0d():
    bit(0x01, _D[0])
    return 8


def bit0e():
    bit(0x01, _E[0])
    return 8


def bit0h():
    bit(0x01, _H[0])
    return 8


def bit0l():
    bit(0x01, _L[0])
    return 8


def bit0fromhl():
    bit(0x01, memory.peekb(_HL[0]))
    return 12


def bit0a():
    bit(0x01, _A[0])
    return 8


# BIT 1, *
def bit1b():
    bit(0x02, _B[0])
    return 8


def bit1c():
    bit(0x02, _C[0])
    return 8


def bit1d():
    bit(0x02, _D[0])
    return 8


def bit1e():
    bit(0x02, _E[0])
    return 8


def bit1h():
    bit(0x02, _H[0])
    return 8


def bit1l():
    bit(0x02, _L[0])
    return 8


def bit1fromhl():
    bit(0x02, memory.peekb(_HL[0]))
    return 12


def bit1a():
    bit(0x02, _A[0])
    return 8


# BIT 2, *
def bit2b():
    bit(0x04, _B[0])
    return 8


def bit2c():
    bit(0x04, _C[0])
    return 8


def bit2d():
    bit(0x04, _D[0])
    return 8


def bit2e():
    bit(0x04, _E[0])
    return 8


def bit2h():
    bit(0x04, _H[0])
    return 8


def bit2l():
    bit(0x04, _L[0])
    return 8


def bit2fromhl():
    bit(0x04, memory.peekb(_HL[0]))
    return 12


def bit2a():
    bit(0x04, _A[0])
    return 8


# BIT 3, *
def bit3b():
    bit(0x08, _B[0])
    return 8


def bit3c():
    bit(0x08, _C[0])
    return 8


def bit3d():
    bit(0x08, _D[0])
    return 8


def bit3e():
    bit(0x08, _E[0])
    return 8


def bit3h():
    bit(0x08, _H[0])
    return 8


def bit3l():
    bit(0x08, _L[0])
    return 8


def bit3fromhl():
    bit(0x08, memory.peekb(_HL[0]))
    return 12


def bit3a():
    bit(0x08, _A[0])
    return 8


# BIT 4, *
def bit4b():
    bit(0x10, _B[0])
    return 8


def bit4c():
    bit(0x10, _C[0])
    return 8


def bit4d():
    bit(0x10, _D[0])
    return 8


def bit4e():
    bit(0x10, _E[0])
    return 8


def bit4h():
    bit(0x10, _H[0])
    return 8


def bit4l():
    bit(0x10, _L[0])
    return 8


def bit4fromhl():
    bit(0x10, memory.peekb(_HL[0]))
    return 12


def bit4a():
    bit(0x10, _A[0])
    return 8


# BIT 5, *
def bit5b():
    bit(0x20, _B[0])
    return 8


def bit5c():
    bit(0x20, _C[0])
    return 8


def bit5d():
    bit(0x20, _D[0])
    return 8


def bit5e():
    bit(0x20, _E[0])
    return 8


def bit5h():
    bit(0x20, _H[0])
    return 8


def bit5l():
    bit(0x20, _L[0])
    return 8


def bit5fromhl():
    bit(0x20, memory.peekb(_HL[0]))
    return 12


def bit5a():
    bit(0x20, _A[0])
    return 8


# BIT 6, *
def bit6b():
    bit(0x40, _B[0])
    return 8


def bit6c():
    bit(0x40, _C[0])
    return 8


def bit6d():
    bit(0x40, _D[0])
    return 8


def bit6e():
    bit(0x40, _E[0])
    return 8


def bit6h():
    bit(0x40, _H[0])
    return 8


def bit6l():
    bit(0x40, _L[0])
    return 8


def bit6fromhl():
    bit(0x40, memory.peekb(_HL[0]))
    return 12


def bit6a():
    bit(0x40, _A[0])
    return 8


# BIT 7, *
def bit7b():
    bit(0x80, _B[0])
    return 8


def bit7c():
    bit(0x80, _C[0])
    return 8


def bit7d():
    bit(0x80, _D[0])
    return 8


def bit7e():
    bit(0x80, _E[0])
    return 8


def bit7h():
    bit(0x80, _H[0])
    return 8


def bit7l():
    bit(0x80, _L[0])
    return 8


def bit7fromhl():
    bit(0x80, memory.peekb(_HL[0]))
    return 12


def bit7a():
    bit(0x80, _A[0])
    return 8


# RES 0, *
def res0b():
    _B[0] = res(0x01, _B[0])
    return 8


def res0c():
    _C[0] = res(0x01, _C[0])
    return 8


def res0d():
    _D[0] = res(0x01, _D[0])
    return 8


def res0e():
    _E[0] = res(0x01, _E[0])
    return 8


def res0h():
    _H[0] = res(0x01, _H[0])
    return 8


def res0l():
    _L[0] = res(0x01, _L[0])
    return 8


def res0fromhl():
    memory.pokeb(_HL[0], res(0x01, memory.peekb(_HL[0])))
    return 15


def res0a():
    _A[0] = res(0x01, _A[0])
    return 8


# RES 1, *
def res1b():
    _B[0] = res(0x02, _B[0])
    return 8


def res1c():
    _C[0] = res(0x02, _C[0])
    return 8


def res1d():
    _D[0] = res(0x02, _D[0])
    return 8


def res1e():
    _E[0] = res(0x02, _E[0])
    return 8


def res1h():
    _H[0] = res(0x02, _H[0])
    return 8


def res1l():
    _L[0] = res(0x02, _L[0])
    return 8


def res1fromhl():
    memory.pokeb(_HL[0], res(0x02, memory.peekb(_HL[0])))
    return 15


def res1a():
    _A[0] = res(0x02, _A[0])
    return 8


# RES 2, *
def res2b():
    _B[0] = res(0x04, _B[0])
    return 8


def res2c():
    _C[0] = res(0x04, _C[0])
    return 8


def res2d():
    _D[0] = res(0x04, _D[0])
    return 8


def res2e():
    _E[0] = res(0x04, _E[0])
    return 8


def res2h():
    _H[0] = res(0x04, _H[0])
    return 8


def res2l():
    _L[0] = res(0x04, _L[0])
    return 8


def res2fromhl():
    memory.pokeb(_HL[0], res(0x04, memory.peekb(_HL[0])))
    return 15


def res2a():
    _A[0] = res(0x04, _A[0])
    return 8


# RES 3, *
def res3b():
    _B[0] = res(0x08, _B[0])
    return 8


def res3c():
    _C[0] = res(0x08, _C[0])
    return 8


def res3d():
    _D[0] = res(0x08, _D[0])
    return 8


def res3e():
    _E[0] = res(0x08, _E[0])
    return 8


def res3h():
    _H[0] = res(0x08, _H[0])
    return 8


def res3l():
    _L[0] = res(0x08, _L[0])
    return 8


def res3fromhl():
    memory.pokeb(_HL[0], res(0x08, memory.peekb(_HL[0])))
    return 15


def res3a():
    _A[0] = res(0x08, _A[0])
    return 8


# RES 4, *
def res4b():
    _B[0] = res(0x10, _B[0])
    return 8


def res4c():
    _C[0] = res(0x10, _C[0])
    return 8


def res4d():
    _D[0] = res(0x10, _D[0])
    return 8


def res4e():
    _E[0] = res(0x10, _E[0])
    return 8


def res4h():
    _H[0] = res(0x10, _H[0])
    return 8


def res4l():
    _L[0] = res(0x10, _L[0])
    return 8


def res4fromhl():
    memory.pokeb(_HL[0], res(0x10, memory.peekb(_HL[0])))
    return 15


def res4a():
    _A[0] = res(0x10, _A[0])
    return 8


# RES 5, *
def res5b():
    _B[0] = res(0x20, _B[0])
    return 8


def res5c():
    _C[0] = res(0x20, _C[0])
    return 8


def res5d():
    _D[0] = res(0x20, _D[0])
    return 8


def res5e():
    _E[0] = res(0x20, _E[0])
    return 8


def res5h():
    _H[0] = res(0x20, _H[0])
    return 8


def res5l():
    _L[0] = res(0x20, _L[0])
    return 8


def res5fromhl():
    memory.pokeb(_HL[0], res(0x20, memory.peekb(_HL[0])))
    return 15


def res5a():
    _A[0] = res(0x20, _A[0])
    return 8


# RES 6, *
def res6b():
    _B[0] = res(0x40, _B[0])
    return 8


def res6c():
    _C[0] = res(0x40, _C[0])
    return 8


def res6d():
    _D[0] = res(0x40, _D[0])
    return 8


def res6e():
    _E[0] = res(0x40, _E[0])
    return 8


def res6h():
    _H[0] = res(0x40, _H[0])
    return 8


def res6l():
    _L[0] = res(0x40, _L[0])
    return 8


def res6fromhl():
    memory.pokeb(_HL[0], res(0x40, memory.peekb(_HL[0])))
    return 15


def res6a():
    _A[0] = res(0x40, _A[0])
    return 8


# RES 7, *
def res7b():
    _B[0] = res(0x80, _B[0])
    return 8


def res7c():
    _C[0] = res(0x80, _C[0])
    return 8


def res7d():
    _D[0] = res(0x80, _D[0])
    return 8


def res7e():
    _E[0] = res(0x80, _E[0])
    return 8


def res7h():
    _H[0] = res(0x80, _H[0])
    return 8


def res7l():
    _L[0] = res(0x80, _L[0])
    return 8


def res7fromhl():
    memory.pokeb(_HL[0], res(0x80, memory.peekb(_HL[0])))
    return 15


def res7a():
    _A[0] = res(0x80, _A[0])
    return 8


# SET 0, *
def set0b():
    _B[0] = set(0x01, _B[0])
    return 8


def set0c():
    _C[0] = set(0x01, _C[0])
    return 8


def set0d():
    _D[0] = set(0x01, _D[0])
    return 8


def set0e():
    _E[0] = set(0x01, _E[0])
    return 8


def set0h():
    _H[0] = set(0x01, _H[0])
    return 8


def set0l():
    _L[0] = set(0x01, _L[0])
    return 8


def set0fromhl():
    memory.pokeb(_HL[0], set(0x01, memory.peekb(_HL[0])))
    return 15


def set0a():
    _A[0] = set(0x01, _A[0])
    return 8


# SET 1, *
def set1b():
    _B[0] = set(0x02, _B[0])
    return 8


def set1c():
    _C[0] = set(0x02, _C[0])
    return 8


def set1d():
    _D[0] = set(0x02, _D[0])
    return 8


def set1e():
    _E[0] = set(0x02, _E[0])
    return 8


def set1h():
    _H[0] = set(0x02, _H[0])
    return 8


def set1l():
    _L[0] = set(0x02, _L[0])
    return 8


def set1fromhl():
    memory.pokeb(_HL[0], set(0x02, memory.peekb(_HL[0])))
    return 15


def set1a():
    _A[0] = set(0x02, _A[0])
    return 8


# SET 2, *
def set2b():
    _B[0] = set(0x04, _B[0])
    return 8


def set2c():
    _C[0] = set(0x04, _C[0])
    return 8


def set2d():
    _D[0] = set(0x04, _D[0])
    return 8


def set2e():
    _E[0] = set(0x04, _E[0])
    return 8


def set2h():
    _H[0] = set(0x04, _H[0])
    return 8


def set2l():
    _L[0] = set(0x04, _L[0])
    return 8


def set2fromhl():
    memory.pokeb(_HL[0], set(0x04, memory.peekb(_HL[0])))
    return 15


def set2a():
    _A[0] = set(0x04, _A[0])
    return 8


# SET 3, *
def set3b():
    _B[0] = set(0x08, _B[0])
    return 8


def set3c():
    _C[0] = set(0x08, _C[0])
    return 8


def set3d():
    _D[0] = set(0x08, _D[0])
    return 8


def set3e():
    _E[0] = set(0x08, _E[0])
    return 8


def set3h():
    _H[0] = set(0x08, _H[0])
    return 8


def set3l():
    _L[0] = set(0x08, _L[0])
    return 8


def set3fromhl():
    memory.peekb(_HL[0], set(0x08, memory.peekb(_HL[0])))
    return 15


def set3a():
    _A[0] = set(0x08, _A[0])
    return 8


# SET 4, *
def set4b():
    _B[0] = set(0x10, _B[0])
    return 8


def set4c():
    _C[0] = set(0x10, _C[0])
    return 8


def set4d():
    _D[0] = set(0x10, _D[0])
    return 8


def set4e():
    _E[0] = set(0x10, _E[0])
    return 8


def set4h():
    _H[0] = set(0x10, _H[0])
    return 8


def set4l():
    _L[0] = set(0x10, _L[0])
    return 8


def set4fromhl():
    memory.pokeb(_HL[0], set(0x10, memory.peekb(_HL[0])))
    return 15


def set4a():
    _A[0] = set(0x10, _A[0])
    return 8


# SET 5, *
def set5b():
    _B[0] = set(0x20, _B[0])
    return 8


def set5c():
    _C[0] = set(0x20, _C[0])
    return 8


def set5d():
    _D[0] = set(0x20, _D[0])
    return 8


def set5e():
    _E[0] = set(0x20, _E[0])
    return 8


def set5h():
    _H[0] = set(0x20, _H[0])
    return 8


def set5l():
    _L[0] = set(0x20, _L[0])
    return 8


def set5fromhl():
    memory.pokeb(_HL[0], set(0x20, memory.peekb(_HL[0])))
    return 15


def set5a():
    _A[0] = set(0x20, _A[0])
    return 8


# SET 6, *
def set6b():
    _B[0] = set(0x40, _B[0])
    return 8


def set6c():
    _C[0] = set(0x40, _C[0])
    return 8


def set6d():
    _D[0] = set(0x40, _D[0])
    return 8


def set6e():
    _E[0] = set(0x40, _E[0])
    return 8


def set6h():
    _H[0] = set(0x40, _H[0])
    return 8


def set6l():
    _L[0] = set(0x40, _L[0])
    return 8


def set6fromhl():
    memory.pokeb(_HL[0], set(0x40, memory.peekb(_HL[0])))
    return 15


def set6a():
    _A[0] = set(0x40, _A[0])
    return 8


# SET 7, *
def set7b():
    _B[0] = set(0x80, _B[0])
    return 8


def set7c():
    _C[0] = set(0x80, _C[0])
    return 8


def set7d():
    _D[0] = set(0x80, _D[0])
    return 8


def set7e():
    _E[0] = set(0x80, _E[0])
    return 8


def set7h():
    _H[0] = set(0x80, _H[0])
    return 8


def set7l():
    _L[0] = set(0x80, _L[0])
    return 8


def set7fromhl():
    memory.pokeb(_HL[0], set(0x80, memory.peekb(_HL[0])))
    return 15


def set7a():
    _A[0] = set(0x80, _A[0])
    return 8


_cbdict = {
    0: rlcb, 1: rlcc, 2: rlcd, 3: rlce, 4: rlch, 5: rlcl, 6: rlcfromhl, 7: rlc_a,
    8: rrcb, 9: rrcc, 10: rrcd, 11: rrce, 12: rrch, 13: rrcl, 14: rrcfromhl, 15: rrc_a,
    16: rlb, 17: rl_c, 18: rld, 19: rle, 20: rlh, 21: rll, 22: rlfromhl, 23: rl_a,
    24: rrb, 25: rr_c, 26: rrd, 27: rre, 28: rrh, 29: rrl, 30: rrfromhl, 31: rr_a,
    32: slab, 33: slac, 34: slad, 35: slae, 36: slah, 37: slal, 38: slafromhl, 39: sla_a,
    40: srab, 41: srac, 42: srad, 43: srae, 44: srah, 45: sral, 46: srafromhl, 47: sra_a,
    48: slsb, 49: slsc, 50: slsd, 51: slse, 52: slsh, 53: slsl, 54: slsfromhl, 55: sls_a,
    56: srlb, 57: srlc, 58: srld, 59: srle, 60: srlh, 61: srll, 62: srlfromhl, 63: srl_a,
    64: bit0b, 65: bit0c, 66: bit0d, 67: bit0e, 68: bit0h, 69: bit0l, 70: bit0fromhl, 71: bit0a,
    72: bit1b, 73: bit1c, 74: bit1d, 75: bit1e, 76: bit1h, 77: bit1l, 78: bit1fromhl, 79: bit1a,
    80: bit2b, 81: bit2c, 82: bit2d, 83: bit2e, 84: bit2h, 85: bit2l, 86: bit2fromhl, 87: bit2a,
    88: bit3b, 89: bit3c, 90: bit3d, 91: bit3e, 92: bit3h, 93: bit3l, 94: bit3fromhl, 95: bit3a,
    96: bit4b, 97: bit4c, 98: bit4d, 99: bit4e, 100: bit4h, 101: bit4l, 102: bit4fromhl, 103: bit4a,
    104: bit5b, 105: bit5c, 106: bit5d, 107: bit5e, 108: bit5h, 109: bit5l, 110: bit5fromhl, 111: bit5a,
    112: bit6b, 113: bit6c, 114: bit6d, 115: bit6e, 116: bit6h, 117: bit6l, 118: bit6fromhl, 119: bit6a,
    120: bit7b, 121: bit7c, 122: bit7d, 123: bit7e, 124: bit7h, 125: bit7l, 126: bit7fromhl, 127: bit7a,
    128: res0b, 129: res0c, 130: res0d, 131: res0e, 132: res0h, 133: res0l, 134: res0fromhl, 135: res0a,
    136: res1b, 137: res1c, 138: res1d, 139: res1e, 140: res1h, 141: res1l, 142: res1fromhl, 143: res1a,
    144: res2b, 145: res2c, 146: res2d, 147: res2e, 148: res2h, 149: res2l, 150: res2fromhl, 151: res2a,
    152: res3b, 153: res3c, 154: res3d, 155: res3e, 156: res3h, 157: res3l, 158: res3fromhl, 159: res3a,
    160: res4b, 161: res4c, 162: res4d, 163: res4e, 164: res4h, 165: res4l, 166: res4fromhl, 167: res4a,
    168: res5b, 169: res5c, 170: res5d, 171: res5e, 172: res5h, 173: res5l, 174: res5fromhl, 175: res5a,
    176: res6b, 177: res6c, 178: res6d, 179: res6e, 180: res6h, 181: res6l, 182: res6fromhl, 183: res6a,
    184: res7b, 185: res7c, 186: res7d, 187: res7e, 188: res7h, 189: res7l, 190: res7fromhl, 191: res7a,
    192: res0b, 193: res0c, 194: res0d, 195: res0e, 196: res0h, 197: res0l, 198: res0fromhl, 199: res0a,
    200: res1b, 201: res1c, 202: res1d, 203: res1e, 204: res1h, 205: res1l, 206: res1fromhl, 207: res1a,
    208: res2b, 209: res2c, 210: res2d, 211: res2e, 212: res2h, 213: res2l, 214: res2fromhl, 215: res2a,
    216: res3b, 217: res3c, 218: res3d, 219: res3e, 220: res3h, 221: res3l, 222: res3fromhl, 223: res3a,
    224: res4b, 225: res4c, 226: res4d, 227: res4e, 228: res4h, 229: res4l, 230: res4fromhl, 231: res4a,
    232: res5b, 233: res5c, 234: res5d, 235: res5e, 236: res5h, 237: res5l, 238: res5fromhl, 239: res5a,
    240: res6b, 241: res6c, 242: res6d, 243: res6e, 244: res6h, 245: res6l, 246: res6fromhl, 247: res6a,
    248: res7b, 249: res7c, 250: res7d, 251: res7e, 252: res7h, 253: res7l, 254: res7fromhl, 255: res7a
}


def cb():
    global _cbdict
    inc_r()
    opcode = (nxtpcb())
    return _cbdict.get(opcode)()


def outna():
    ports.port_out(nxtpcb(), _A[0])
    return 11


def inan():
    _A[0] = ports.port_in(_A[0] << 8 | nxtpcb())
    return 11


def exsphl():
    t = _HL[0]
    _HL[0] = memory.peekw(_SP[0])
    memory.pokew(_SP[0], t)
    return 19


def exdehl():
    _HL[0], _DE[0] = _DE[0], _HL[0]
    return 4


def di():
    global _IFF1, _IFF2
    _IFF1 = False
    _IFF2 = False
    return 4


def ei():
    global _IFF1, _IFF2
    _IFF1 = True
    _IFF2 = True
    return 4


# CALL cc,nn
def callnznn():
    global _fZ
    if not _fZ:
        t = nxtpcw()
        pushpc()
        _PC[0] = t
        return 17
    else:
        _PC[0] = (_PC[0] + 2) % 65536
        return 10


def callznn():
    global _fZ
    if _fZ:
        t = nxtpcw()
        pushpc()
        _PC[0] = t
        return 17
    else:
        _PC[0] = (_PC[0] + 2) % 65536
        return 10


def callncnn():
    global _fC
    if not _fC:
        t = nxtpcw()
        pushpc()
        _PC[0] = t
        return 17
    else:
        _PC[0] = (_PC[0] + 2) % 65536
        return 10


def callcnn():
    global _fC
    if _fC:
        t = nxtpcw()
        pushpc()
        _PC[0] = t
        return 17
    else:
        _PC[0] = (_PC[0] + 2) % 65536
        return 10


def callponn():
    global _fPV
    if not _fPV:
        t = nxtpcw()
        pushpc()
        _PC[0] = t
        return 17
    else:
        _PC[0] = (_PC[0] + 2) % 65536
        return 10


def callpenn():
    global _fPV
    if _fPV:
        t = nxtpcw()
        pushpc()
        _PC[0] = t
        return 17
    else:
        _PC[0] = (_PC[0] + 2) % 65536
        return 10


def callpnn():
    global _fS
    if not _fS:
        t = nxtpcw()
        pushpc()
        _PC[0] = t
        return 17
    else:
        _PC[0] = (_PC[0] + 2) % 65536
        return 10


def callmnn():
    global _fS
    if _fS:
        t = nxtpcw()
        pushpc()
        _PC[0] = t
        return 17
    else:
        _PC[0] = (_PC[0] + 2) % 65536
        return 10


# PUSH
def pushbc():
    pushw(_BC[0])
    return 11


def pushde():
    pushw(_DE[0])
    return 11


def pushhl():
    pushw(_HL[0])
    return 11


def pushaf():
    global _fS, _fZ, _f5, _fH, _f3, _fPV, _fN, _fC
    _F[0] = (F_S if _fS else 0) + \
        (F_Z if _fZ else 0) + \
        (F_5 if _f5 else 0) + \
        (F_H if _fH else 0) + \
        (F_3 if _f3 else 0) + \
        (F_PV if _fPV else 0) + \
        (F_N if _fN else 0) + \
        (F_C if _fC else 0)
    pushw(_AF[0])
    return 11


# op A,N
def addan():
    add_a(nxtpcb())
    return 7


def adcan():
    adc_a(nxtpcb())
    return 7


def suban():
    sub_a(nxtpcb())
    return 7


def sbcan():
    sbc_a(nxtpcb())
    return 7


def andan():
    and_a(nxtpcb())
    return 7


def xoran():
    xor_a(nxtpcb())
    return 7


def oran():
    or_a(nxtpcb())
    return 7


def cpan():
    cp_a(nxtpcb())
    return 7


# RST n
def rst0():
    pushpc()
    _PC[0] = 0
    return 11


def rst8():
    pushpc()
    _PC[0] = 8
    return 11


def rst16():
    pushpc()
    _PC[0] = 16
    return 11


def rst24():
    pushpc()
    _PC[0] = 24
    return 11


def rst32():
    pushpc()
    _PC[0] = 32
    return 11


def rst40():
    pushpc()
    _PC[0] = 40
    return 11


def rst48():
    pushpc()
    _PC[0] = 48
    return 11


def rst56():
    pushpc()
    _PC[0] = 56
    return 11


# Various
def callnn():
    t = nxtpcw()
    pushpc()
    _PC[0] = t
    return 17


def ix():
    global _ID, _IDL, _IDH, _IX, _IXL, _IXH
    inc_r()
    _ID = _IX
    _IDL = _IXL
    _IDH = _IXH
    return execute_id()


# ED prefix
# IN r,(c)
def inbfrombc():
    _B[0] = in_bc()
    return 12


def incfrombc():
    _C[0] = in_bc()
    return 12


def indfrombc():
    _D[0] = in_bc()
    return 12


def inefrombc():
    _E[0] = in_bc()
    return 12


def inhfrombc():
    _H[0] = in_bc()
    return 12


def inlfrombc():
    _L[0] = in_bc()
    return 12


def infrombc():
    in_bc()
    return 12


def inafrombc():
    _A[0] = in_bc()
    return 12


# OUT (c),r
def outtocb():
    ports.port_out(_BC[0], _B[0])
    return 12


def outtocc():
    ports.port_out(_BC[0], _C[0])
    return 12


def outtocd():
    ports.port_out(_BC[0], _D[0])
    return 12


def outtoce():
    ports.port_out(_BC[0], _E[0])
    return 12


def outtoch():
    ports.port_out(_BC[0], _H[0])
    return 12


def outtocl():
    ports.port_out(_BC[0], _L[0])
    return 12


def outtoc0():
    ports.port_out(_BC[0], 0)
    return 12


def outtoca():
    ports.port_out(_BC[0], _A[0])
    return 12


# SBC/ADC HL,ss
def sbchlbc():
    _HL[0] = sbc16(_HL[0], _BC[0])
    return 15


def adchlbc():
    _HL[0] = adc16(_HL[0], _BC[0])
    return 15


def sbchlde():
    _HL[0] = sbc16(_HL[0], _DE[0])
    return 15


def adchlde():
    _HL[0] = adc16(_HL[0], _DE[0])
    return 15


def sbchlhl():
    hl = _HL[0]
    _HL[0] = sbc16(hl, hl)
    return 15


def adchlhl():
    hl = _HL[0]
    _HL[0] = adc16(hl, hl)
    return 15


def sbchlsp():
    _HL[0] = sbc16(_HL[0], _SP[0])
    return 15


def adchlsp():
    _HL[0] = adc16(_HL[0], _SP[0])
    return 15


# LD (nn),ss, LD ss,(nn)
def ldtonnbc():
    memory.pokew(nxtpcw(), _BC[0])
    return 20


def ldbcfromnn():
    _BC[0] = memory.peekw(nxtpcw())
    return 20


def ldtonnde():
    memory.pokew(nxtpcw(), _DE[0])
    return 20


def lddefromnn():
    _DE[0] = memory.peekw(nxtpcw())
    return 20


def edldtonnhl():
    return ldtonnhl() + 4


def edldhlfromnn():
    return ldhlfromnn() + 4


def ldtonnsp():
    memory.pokew(nxtpcw(), _SP[0])
    return 20


def ldspfromnn():
    _SP[0] = memory.peekw(nxtpcw())
    return 20


# NEG
def nega():
    global _fPV, _fC
    t = _A[0]
    _A[0] = 0
    sub_a(t)
    _fPV = t == 0x80
    _fC = t != 0
    return 8


# RETn
def retn():
    global _IFF1, _IFF2
    _IFF1 = _IFF2
    poppc()
    return 14


def reti():
    poppc()
    return 14


# IM x
def im0():
    global _IM
    _IM = IM0
    return 8


def im1():
    global _IM
    _IM = IM1
    return 8


def im2():
    global _IM
    _IM = IM2
    return 8


# LD A,s / LD s,A / RxD
def ldia():
    _I[0] = _A[0]
    return 9


def ldra():
    global _R
    _R = _A[0]
    return 9


def ldai():
    global _fS, _f3, _f5, _fZ, _fPV, _fH, _fN, _IFF2
    ans = _I[0]
    _fS = ans > 0x7f
    _f3 = (ans & F_3) != 0
    _f5 = (ans & F_5) != 0
    _fZ = ans == 0
    _fPV = _IFF2
    _fH = False
    _FN  = False
    _A[0] = ans
    return 9


# Load a with r - (NOT CHECKED)
def ldar():
    global _fS, _f3, _f5, _fZ, _fPV, _fH, _fN, _IFF2, _R
    _A[0] = _R
    _fS = _A[0] > 0x7f
    _f3 = (_A[0] & F_3) != 0
    _f5 = (_A[0] & F_5) != 0
    _fZ = _A[0] == 0
    _fPV = _IFF2
    _fH = False
    _fN = False
    return 9


def rrda():
    global _fS, _f3, _f5, _fZ, _fPV, _fH, _fN
    ans = _A[0]
    t = memory.peekb(_HL[0])
    q = t

    t = ((t >> 4) + (ans << 4)) % 256
    ans = (ans & 0xf0) + (q % 16)
    memory.pokeb(_HL[0], t)
    _fS = (ans & F_S) != 0
    _f3 = (ans & F_3) != 0
    _f5 = (ans & F_5) != 0
    _fZ = ans == 0
    _fPV = parity[ans]
    _fH = False
    _fN = False
    _A[0] = ans
    return 18


def rlda():
    global _fS, _f3, _f5, _fZ, _fPV, _fH, _fN
    ans = _A[0]
    t = memory.peekb(_HL[0])
    q = t

    t = ((t << 4) + (ans % 16)) % 256
    ans = ((ans & 0xf0) + (q >> 4)) % 256
    memory.pokeb(_HL[0], t)
    _fS = (ans & F_S) != 0
    _f3 = (ans & F_3) != 0
    _f5 = (ans & F_5) != 0
    _fZ = ans == 0
    _fPV = parity[ans]
    _fH = False
    _fN = False
    _A[0] = ans
    return 18


# xxI
def ldi():
    global _fPV, _fH, _fN
    memory.pokeb(_DE[0], memory.peekb(_HL[0]))
    _DE[0] = inc16(_DE[0])
    _HL[0] = inc16(_HL[0])
    _BC[0] = dec16(_BC[0])
    _fPV = _BC[0] != 0
    _fH = False
    _fN = False
    return 16


def cpi():
    global _fPV, _fN, _fC
    c = _fC
    cp_a(memory.peekb(_HL[0]))
    _HL[0] = inc16(_HL[0])
    _BC[0] = dec16(_BC[0])
    _fPV = _BC[0] != 0
    _fC = c
    _fN = True
    return 16


def ini():
    global _fPV, _fN, _fC, _fZ
    c = _fC
    memory.pokeb(_HL[0], ports.port_in(_BC[0]))
    _HL[0] = inc16(_HL[0])
    _B[0] = qdec8(_B[0])
    _fC = c
    _fN = False
    _fZ = _B[0] == 0
    return 16


def outi():
    global _fPV, _fN, _fC
    c = _fC
    ports.port_out(_BC[0], memory.peekb(_HL[0]))
    _HL[0] = inc16(_HL[0])
    _B[0] = qdec8(_B[0])
    _fC = c
    _fN = False
    _fZ = _B[0] == 0
    return 16


# xxD
def ldd():
    global _fPV, _fH, _fN
    memory.pokeb(_DE[0], memory.peekb(_HL[0]))
    _DE[0] = dec16(_DE[0])
    _HL[0] = dec16(_HL[0])
    _BC[0] = dec16(_BC[0])
    _fPV = _BC[0] != 0
    _fH = False
    _fN = False
    return 16


def cpd():
    global _fPV, _fN, _fC
    c = _fC
    cp_a(memory.peekb(_HL[0]))
    _HL[0] = dec16(_HL[0])
    _BC[0] = dec16(_BC[0])
    _fC = c
    _fN = True
    _fPV = _BC[0] != 0
    return 16


def ind():
    global _fZ, _fN
    memory.pokeb(_HL[0], ports.port_in(_BC[0]))
    _HL[0] = dec16(_HL[0])
    _B[0] = qdec8(_B[0])
    _fN = True
    _fZ = _B[0] == 0
    return 16


def outd():
    global _fZ, _fN
    ports.port_out(_BC[0], memory.peekb(_HL[0]))
    _HL[0] = dec16(_HL[0])
    _B[0] = qdec8(_B[0])
    _fN = True
    _fZ = _B[0] == 0
    return 16


# xxIR
def ldir():
    global _fPV, _R7_b, local_tstates, _fN, _fH
    _fPV = True
    while True:
        memory.pokeb(_DE[0], memory.peekb(_HL[0]))
        _DE[0] = (_DE[0] + 1) % 65536
        _HL[0] = (_HL[0] + 1) % 65536
        _BC[0] = (_BC[0] - 1) % 65536
        _R_b[0] = (_R_b[0] + 2) % 128 + _R7_b
        if _BC[0] == 0:
            break
        local_tstates += 21
        check_tstates()
    _fPV = False
    _fN = False
    _fH = False
    return 16


def cpir():
    global _fPV, _fN, _fC, _fZ, _R7_b, local_tstates
    c = _fC
    _fPV = True
    while True:
        cp_a(memory.peekb(_HL[0]))
        _HL[0] = (_HL[0] + 1) % 65536
        _BC[0] = (_BC[0] - 1) % 65536
        _R_b[0] = (_R_b[0] + 2) % 128 + _R7_b
        if _BC[0] == 0 or _fZ:
            break
        local_tstates += 21
        check_tstates()
    _fC = c
    _fN = True
    _fPV = _BC[0] != 0
    return 16


def inir():
    global _fN, _fC, _fZ, _R7_b, local_tstates
    while True:
        memory.pokeb(_HL, ports.port_in(_BC[0]))
        _HL[0] = (_HL[0] + 1) % 65536
        _B[0] = (_B[0] - 1) % 256
        _R_b[0] = (_R_b[0] + 2) % 128 + _R7_b
        if _B[0] == 0:
            break
        local_tstates += 21
        check_tstates()
    _fZ = True
    _fC = False
    _fN = False
    return 16

def otir():
    global _fN, _fZ, _R7_b, local_tstates
    while True:
        ports.port_out(_BC[0], memory.peekb(_HL[0]))
        _HL[0] = (_HL[0] + 1) % 65536
        _B[0] = (_B[0] - 1) % 256
        _R_b[0] = (_R_b[0] + 2) % 128 + _R7_b
        if _B[0] == 0:
            break
        local_tstates += 21
        check_tstates()
    _fZ = True
    _fN = False
    return 16


# xxDR
def lddr():
    global _fPV, _R7_b, local_tstates, _fH, _fN
    _fPV = True
    while True:
        memory.pokeb(_DE[0], memory.peekb(_HL[0]))
        _DE[0] = (_DE[0] - 1) % 65536
        _HL[0] = (_HL[0] - 1) % 65536
        _BC[0] = (_BC[0] - 1) % 65536
        _R_b[0] = (_R_b[0] + 2) % 128 + _R7_b
        if _BC[0] == 0:
            break
        local_tstates += 21
        check_tstates()
    _fPV = False
    _fH = False
    _fN = False
    return 16


def cpdr():
    global _fPV, _fN, _fC, _fZ, _R7_b, local_tstates
    c = _fC
    _fPV = True
    while True:
        cp_a(memory.peekb(_HL[0]))
        _HL[0] = (_HL[0] - 1) % 65536
        _BC[0] = (_BC[0] - 1) % 65536
        _R_b[0] = (_R_b[0] + 2) % 128 + _R7_b
        if _BC[0] == 0 or _fZ:
            break
        local_tstates += 21
        check_tstates()
    _fC = c
    _fN = True
    _fPV = _BC[0] != 0
    return 16


def indr():
    global _fN, _fC, _fZ, _R7_b, local_tstates
    while True:
        memory.pokeb(_HL, ports.port_in(_BC[0]))
        _HL[0] = (_HL[0] - 1) % 65536
        _B[0] = (_B[0] - 1) % 256
        _R_b[0] = (_R_b[0] + 2) % 128 + _R7_b
        if _B[0] == 0:
            break
        local_tstates += 21
        check_tstates()
    _fZ = True
    _fC = False
    _fN = False
    return 16

def otdr():
    global _fN, _fZ, _R7_b, local_tstates
    while True:
        ports.port_out(_BC[0], memory.peekb(_HL[0]))
        _HL[0] = (_HL[0] - 1) % 65536
        _B[0] = (_B[0] - 1) % 256
        _R_b[0] = (_R_b[0] + 2) % 128 + _R7_b
        if _B[0] == 0:
            break
        local_tstates += 21
        check_tstates()
    _fZ = True
    _fN = False
    return 16


_eddict = {
    64: inbfrombc, 72: incfrombc, 80: indfrombc, 88: inefrombc, 96: inhfrombc, 104: inlfrombc, 112: infrombc, 120: inafrombc,
    65: outtocb, 73: outtocc, 81: outtocd, 89: outtoce, 97: outtoch, 105: outtocl, 113: outtoc0, 121: outtoca,
    66: sbchlbc, 74: adchlbc, 82: sbchlde, 90: adchlde, 98: sbchlhl, 106: adchlhl, 114: sbchlsp, 122: adchlsp,
    67: ldtonnbc, 75: ldbcfromnn, 83: ldtonnde, 91: lddefromnn, 99: edldtonnhl, 107: edldhlfromnn, 115: ldtonnsp, 123: ldspfromnn,
    68: nega, 76: nega, 84: nega, 92: nega, 100: nega, 108: nega, 116: nega, 124: nega,
    69: retn, 85: retn, 101: retn, 117: retn, 77: reti, 93: reti, 109: reti, 125: reti,
    70: im0, 78: im0, 102: im0, 110: im0, 86: im1, 118: im1, 94: im2, 126: im2,
    71: ldia, 79: ldra, 87: ldai, 95: ldar, 103: rrda, 111: rlda,
    160: ldi, 161: cpi, 162: ini, 163: outi,
    168: ldd, 169: cpd, 170: ind, 171: outd,
    176: ldir, 177: cpir, 178: inir, 179: otir,
    184: lddr, 185: cpdr, 186: indr, 187: otdr
}


def ednop():
    return 8


def ed():
    opcode = nxtpcb()
    return _eddict.get(opcode, ednop)()


def iy():
    global _ID, _IDL, _IDH, _IY, _IYL, _IYH
    inc_r()
    _ID = _IY
    _IDL = _IYL
    _IDH = _IYH
    return execute_id()


main_cmds = {
    0: nop, 8: ex_af_af, 16: djnz, 24: jr, 32: jrnz, 40: jrz, 48: jrnc, 56: jrc,
    1: ldbcnn, 9: addhlbc, 17: lddenn, 25: addhlde, 33: ldhlnn, 41: addhlhl, 49: ldspnn, 57: addhlsp,
    2: ldtobca, 10: ldafrombc, 18: ldtodea, 26: ldafromde, 34: ldtonnhl, 42: ldhlfromnn, 50: ldtonna, 58: ldafromnn,
    3: incbc, 11: decbc, 19: incde, 27: decde, 35: inchl, 43: dechl, 51: incsp, 59: decsp,
    4: incb, 12: incc, 20: incd, 28: ince, 36: inch, 44: incl, 52: incinhl, 60: inca,
    5: decb, 13: decc, 21: decd, 29: dece, 37: dech, 45: decl, 53: decinhl, 61: deca,
    6: ldbn, 14: ldcn, 22: lddn, 30: lden, 38: ldhn, 46: ldln, 54: ldtohln, 62: ldan,
    7: rlca, 15: rrca, 23: rla, 31: rra, 39: daa, 47: cpla, 55: scf, 63: ccf,
    64: ldbb, 65: ldbc, 66: ldbd, 67: ldbe, 68: ldbh, 69: ldbl, 70: ldbfromhl, 71: ldba,
    72: ldcb, 73: ldcc, 74: ldcd, 75: ldce, 76: ldch, 77: ldcl, 78: ldcfromhl, 79: ldca,
    80: lddb, 81: lddc, 82: lddd, 83: ldde, 84: lddh, 85: lddl, 86: lddfromhl, 87: ldda,
    88: ldeb, 89: ldec, 90: lded, 91: ldee, 92: ldeh, 93: ldel, 94: ldefromhl, 95: ldea,
    96: ldhb, 97: ldhc, 98: ldhd, 99: ldhe, 100: ldhh, 101: ldhl, 102: ldhfromhl, 103: ldha,
    104: ldlb, 105: ldlc, 106: ldld, 107: ldle, 108: ldlh, 109: ldll, 110: ldlfromhl, 111: ldla,
    112: ldtohlb, 113: ldtohlc, 114: ldtohld, 115: ldtohle, 116: ldtohlh, 117: ldtohll, 119: ldtohla,
    120: ldab, 121: ldac, 122: ldad, 123: ldae, 124: ldah, 125: ldal, 126: ldafromhl, 127: ldaa,
    128: addab, 129: addac, 130: addad, 131: addae, 132: addah, 133: addal, 134: addafromhl, 135: addaa,
    136: adcab, 137: adcac, 138: adcad, 139: adcae, 140: adcah, 141: adcal, 142: adcafromhl, 143: adcaa,
    144: subab, 145: subac, 146: subad, 147: subae, 148: subah, 149: subal, 150: subafromhl, 151: subaa,
    152: sbcab, 153: sbcac, 154: sbcad, 155: sbcae, 156: sbcah, 157: sbcal, 158: sbcafromhl, 159: sbcaa,
    160: andab, 161: andac, 162: andad, 163: andae, 164: andah, 165: andal, 166: andafromhl, 167: andaa,
    168: xorab, 169: xorac, 170: xorad, 171: xorae, 172: xorah, 173: xoral, 174: xorafromhl, 175: xoraa,
    176: orab, 177: orac, 178: orad, 179: orae, 180: orah, 181: oral, 182: orafromhl, 183: oraa,
    184: cpab, 185: cpac, 186: cpad, 187: cpae, 188: cpah, 189: cpal, 190: cpafromhl, 191: cpaa,
    192: retnz, 200: retz, 208: retnc, 216: retc, 224: retpo, 232: retpe, 240: retp, 248: retm,
    193: popbc, 209: popde, 225: pophl, 241: popaf,
    194: jpnznn, 202: jpznn, 210: jpncnn, 218: jpcnn, 226: jpponn, 234: jppenn, 242: jppnn, 250: jpmnn,
    217: exx, 233: jphl, 249: ldsphl, 201: ret, 195: jpnn, 203: cb, 211: outna, 219: inan, 227: exsphl, 235: exdehl, 243: di, 251: ei,
    196: callnznn, 204: callznn, 212: callncnn, 220: callcnn, 228: callponn, 236: callpenn, 244: callpnn, 252: callmnn,
    197: pushbc, 213: pushde, 229: pushhl, 245: pushaf,
    198: addan, 206: adcan, 214: suban, 222: sbcan, 230: andan, 238: xoran, 246: oran, 254: cpan,
    199: rst0, 207: rst8, 215: rst16, 223: rst24, 231: rst32, 239: rst40, 247: rst48, 255: rst56,
    205: callnn, 221: ix, 237: ed, 253: iy, 
}


# IX, IY ops
# ADD ID, *
def addidbc():
    _ID[0] = add16(_ID[0], _BC[0])
    return 15


def addidde():
    _ID[0] = add16(_ID[0], _DE[0])
    return 15


def addidid():
    id = _ID[0]
    _ID[0] = add16(id, id)
    return 15


def addidsp():
    _ID[0] = add16(_ID[0], _SP[0])
    return 15


# LD ID, nn
def ldidnn():
    _ID[0] = nxtpcw()
    return 14


def ldtonnid():
    memory.pokew(nxtpcw(), _ID[0])
    return 20


def ldidfromnn():
    _ID[0] = memory.peekw(nxtpcw())
    return 20


# INC
def incid():
    _ID[0] = inc16(_ID[0])
    return 10


def incidh():
    _IDH[0] = inc8(_IDH[0])
    return 8


def incidl():
    _IDL[0] = inc8(_IDL[0])
    return 8


def incinidd():
    z = ID_d()
    memory.pokeb(z, inc8(memory.peekb(z)))
    return 23
    

# DEC
def decid():
    _ID[0] = dec16(_ID[0])
    return 10


def decidh():
    _IDH[0] = dec8(_IDH[0])
    return 8


def decidl():
    _IDL[0] = dec8(_IDL[0])
    return 8


def decinidd():
    z = ID_d()
    memory.pokeb(z, dec8(memory.peekb(z)))
    return 23


# LD *, IDH
def ldbidh():
    _B[0] = _IDH[0]
    return 8


def ldcidh():
    _C[0] = _IDH[0]
    return 8


def lddidh():
    _D[0] = _IDH[0]
    return 8


def ldeidh():
    _E[0] = _IDH[0]
    return 8


def ldaidh():
    _A[0] = _IDH[0]
    return 8


# LD *, IDL
def ldbidl():
    _B[0] = _IDL[0]
    return 8


def ldcidl():
    _C[0] = _IDL[0]
    return 8


def lddidl():
    _D[0] = _IDL[0]
    return 8


def ldeidl():
    _E[0] = _IDL[0]
    return 8


def ldaidl():
    _A[0] = _IDL[0]
    return 8


# LD IDH, *
def ldidhb():
    _IDH[0] = _B[0]
    return 8


def ldidhc():
    _IDH[0] = _C[0]
    return 8


def ldidhd():
    _IDH[0] = _D[0]
    return 8


def ldidhe():
    _IDH[0] = _E[0]
    return 8


def ldidhidh():
    return 8


def ldidhidl():
    _IDH[0] = _IDL[0]
    return 8


def ldidhn():
    _IDH[0] = nxtpcb()
    return 11


def ldidha():
    _IDH[0] = _A[0]
    return 8


# LD IDL, *
def ldidlb():
    _IDL[0] = _B[0]
    return 8


def ldidlc():
    _IDL[0] = _C[0]
    return 8


def ldidld():
    _IDL[0] = _D[0]
    return 8


def ldidle():
    _IDL[0] = _E[0]
    return 8


def ldidlidh():
    _IDL[0] = _IDH[0]
    return 8


def ldidlidl():
    return 8


def ldidln():
    _IDL[0] = nxtpcb()
    return 11


def ldidla():
    _IDL[0] = _A[0]
    return 8


# LD *, (ID+d)
def ldbfromidd():
    _B[0] = memory.peekb(ID_d())
    return 19


def ldcfromidd():
    _C[0] = memory.peekb(ID_d())
    return 19


def lddfromidd():
    _D[0] = memory.peekb(ID_d())
    return 19


def ldefromidd():
    _E[0] = memory.peekb(ID_d())
    return 19


def ldhfromidd():
    _H[0] = memory.peekb(ID_d())
    return 19


def ldlfromidd():
    _L[0] = memory.peekb(ID_d())
    return 19


def ldafromidd():
    _A[0] = memory.peekb(ID_d())
    return 19


# LD (ID+d), *
def ldtoiddb():
    memory.pokeb(ID_d(), _B[0])
    return 19


def ldtoiddc():
    memory.pokeb(ID_d(), _C[0])
    return 19


def ldtoiddd():
    memory.pokeb(ID_d(), _D[0])
    return 19


def ldtoidde():
    memory.pokeb(ID_d(), _E[0])
    return 19


def ldtoiddh():
    memory.pokeb(ID_d(), _H[0])
    return 19


def ldtoiddl():
    memory.pokeb(ID_d(), _L[0])
    return 19


def ldtoiddn():
    memory.pokeb(ID_d(), nxtpcb())
    return 19


def ldtoidda():
    memory.pokeb(ID_d(), _A[0])
    return 19


# ADD/ADC A, *
def addaidh():
    add_a(_IDH[0])
    return 8


def addaidl():
    add_a(_IDL[0])
    return 8


def addafromidd():
    add_a(memory.peekb(ID_d()))
    return 19


def adcaidh():
    adc_a(_IDH[0])
    return 8


def adcaidl():
    adc_a(_IDL[0])
    return 8


def adcafromidd():
    adc_a(memory.peekb(ID_d()))
    return 19


# SUB/SBC A, *
def subaidh():
    sub_a(_IDH[0])
    return 8


def subaidl():
    sub_a(_IDL[0])
    return 8


def subafromidd():
    sub_a(memory.peekb(ID_d()))
    return 19


def sbcaidh():
    sbc_a(_IDH[0])
    return 8


def sbcaidl():
    sbc_a(_IDL[0])
    return 8


def sbcafromidd():
    sbc_a(memory.peekb(ID_d()))
    return 19


# Bitwise OPS
def andaidh():
    and_a(_IDH[0])
    return 8


def andaidl():
    and_a(_IDL[0])
    return 8


def andafromidd():
    and_a(memory.peekb(ID_d()))
    return 19


def xoraidh():
    xor_a(_IDH[0])
    return 8


def xoraidl():
    xor_a(_IDL[0])
    return 8


def xorafromidd():
    xor_a(memory.peekb(ID_d()))
    return 19


def oraidh():
    or_a(_IDH[0])
    return 8


def oraidl():
    or_a(_IDL[0])
    return 8


def orafromidd():
    or_a(memory.peekb(ID_d()))
    return 19


#CP A, *
def cpaidh():
    cp_a(_IDH[0])
    return 8


def cpaidl():
    cp_a(_IDL[0])
    return 8


def cpafromidd():
    cp_a(memory.peekb(ID_d()))
    return 19


# Various
def pushid():
    pushw(_ID[0])
    return 15


def popid():
    _ID[0] = popw()
    return 14


def jpid():
    _PC[0] = _ID[0]
    return 8


def ldspid():
    _SP[0] = _ID[0]
    return 10


def exfromspid():
    t = _ID[0]
    sp = _SP[0]
    _ID[0] = memory.peekw(sp)
    memory.pokew(sp, t)
    return 23


# DDCB/FDCB prefix
def idcb():
    # Get index address (offset byte is first)
    z = ID_d()
    # Opcode comes after offset byte
    op = nxtpcb()
    return execute_id_cb(op, z)


_ixiydict = {
    9: addidbc, 25: addidde, 41: addidid, 57: addidsp,
    33: ldidnn, 34: ldtonnid, 42: ldidfromnn,
    35: incid, 36: incidh, 44: incidl, 52: incinidd,
    43: decid, 37: decidh, 45: decidl, 53: decinidd,
    68: ldbidh, 76: ldcidh, 84: lddidh, 92: ldeidh, 124: ldaidh,
    69: ldbidl, 77: ldcidl, 85: lddidl, 93: ldeidl, 125: ldaidl,
    96: ldidhb, 97: ldidhc, 98: ldidhd, 99: ldidhe, 100: ldidhidh, 101: ldidhidl, 38: ldidhn, 103: ldidha,
    104: ldidlb, 105: ldidlc, 106: ldidld, 107: ldidle, 108: ldidlidh, 109: ldidlidl, 46: ldidln, 111: ldidla,
    70: ldbfromidd, 78: ldcfromidd, 86: lddfromidd, 94: ldefromidd, 102: ldhfromidd, 110: ldlfromidd, 126: ldafromidd,
    112: ldtoiddb, 113: ldtoiddc, 114: ldtoiddd, 115: ldtoidde, 116: ldtoiddh, 117: ldtoiddl, 54: ldtoiddn, 119: ldtoidda,
    132: addaidh, 133: addaidl, 134: addafromidd, 140: adcaidh, 141: adcaidl, 142: adcafromidd,
    148: subaidh, 149: subaidl, 150: subafromidd, 156: sbcaidh, 157: sbcaidl, 158: sbcafromidd,
    164: andaidh, 165: andaidl, 166: andafromidd, 172: xoraidh, 173: xoraidl, 174: xorafromidd, 180: oraidh, 181: oraidl, 182: orafromidd,
    188: cpaidh, 189: cpaidl, 190: cpafromidd,
    229: pushid, 225: popid, 233: jpid, 249: ldspid, 227: exfromspid,
    203: idcb
}


def ID_d():
    return (_ID[0] + nxtpcsb()) % 65536


# DDCB/FDCB opcodes
# RLC *
def cbrlcb(z):
    _B[0] = rlc(memory.peekb(z))
    memory.pokeb(z, _B[0])
    return 23

def cbrlcc(z):
    _C[0] = rlc(memory.peekb(z))
    memory.pokeb(z, _C[0])
    return 23


def cbrlcd(z):
    _D[0] = rlc(memory.peekb(z))
    memory.pokeb(z, _D[0])
    return 23


def cbrlce(z):
    _E[0] = rlc(memory.peekb(z))
    memory.pokeb(z, _E[0])
    return 23


def cbrlch(z):
    _H[0] = rlc(memory.peekb(z))
    memory.pokeb(z, _H[0])
    return 23


def cbrlcl(z):
    _L[0] = rlc(memory.peekb(z))
    memory.pokeb(z, _L[0])
    return 23


def cbrlcinhl(z):
    memory.pokeb(z, rlc(memory.peekb(z)))
    return 23


def cbrlca(z):
    _A[0] = rlc(memory.peekb(z))
    memory.pokeb(z, _A[0])
    return 23


# RRC *
def cbrrcb(z):
    _B[0] = rrc(memory.peekb(z))
    memory.pokeb(z, _B[0])
    return 23

def cbrrcc(z):
    _C[0] = rrc(memory.peekb(z))
    memory.pokeb(z, _C[0])
    return 23


def cbrrcd(z):
    _D[0] = rrc(memory.peekb(z))
    memory.pokeb(z, _D[0])
    return 23


def cbrrce(z):
    _E[0] = rrc(memory.peekb(z))
    memory.pokeb(z, _E[0])
    return 23


def cbrrch(z):
    _H[0] = rrc(memory.peekb(z))
    memory.pokeb(z, _H[0])
    return 23


def cbrrcl(z):
    _L[0] = rrc(memory.peekb(z))
    memory.pokeb(z, _L[0])
    return 23


def cbrrcinhl(z):
    memory.pokeb(z, rrc(memory.peekb(z)))
    return 23


def cbrrca(z):
    _A[0] = rrc(memory.peekb(z))
    memory.pokeb(z, _A[0])
    return 23


# RL *
def cbrlb(z):
    _B[0] = rl(memory.peekb(z))
    memory.pokeb(z, _B[0])
    return 23

def cbrlc(z):
    _C[0] = rl(memory.peekb(z))
    memory.pokeb(z, _C[0])
    return 23


def cbrld(z):
    _D[0] = rl(memory.peekb(z))
    memory.pokeb(z, _D[0])
    return 23


def cbrle(z):
    _E[0] = rl(memory.peekb(z))
    memory.pokeb(z, _E[0])
    return 23


def cbrlh(z):
    _H[0] = rl(memory.peekb(z))
    memory.pokeb(z, _H[0])
    return 23


def cbrll(z):
    _L[0] = rl(memory.peekb(z))
    memory.pokeb(z, _L[0])
    return 23


def cbrlinhl(z):
    memory.pokeb(z, rl(memory.peekb(z)))
    return 23


def cbrla(z):
    _A[0] = rl(memory.peekb(z))
    memory.pokeb(z, _A[0])
    return 23


# RR *
def cbrrb(z):
    _B[0] = rr(memory.peekb(z))
    memory.pokeb(z, _B[0])
    return 23

def cbrrc(z):
    _C[0] = rr(memory.peekb(z))
    memory.pokeb(z, _C[0])
    return 23


def cbrrd(z):
    _D[0] = rr(memory.peekb(z))
    memory.pokeb(z, _D[0])
    return 23


def cbrre(z):
    _E[0] = rr(memory.peekb(z))
    memory.pokeb(z, _E[0])
    return 23


def cbrrh(z):
    _H[0] = rr(memory.peekb(z))
    memory.pokeb(z, _H[0])
    return 23


def cbrrl(z):
    _L[0] = rr(memory.peekb(z))
    memory.pokeb(z, _L[0])
    return 23


def cbrrinhl(z):
    memory.pokeb(z, rr(memory.peekb(z)))
    return 23


def cbrra(z):
    _A[0] = rr(memory.peekb(z))
    memory.pokeb(z, _A[0])
    return 23


# SLA *
def cbslab(z):
    _B[0] = sla(memory.peekb(z))
    memory.pokeb(z, _B[0])
    return 23

def cbslac(z):
    _C[0] = sla(memory.peekb(z))
    memory.pokeb(z, _C[0])
    return 23


def cbslad(z):
    _D[0] = sla(memory.peekb(z))
    memory.pokeb(z, _D[0])
    return 23


def cbslae(z):
    _E[0] = sla(memory.peekb(z))
    memory.pokeb(z, _E[0])
    return 23


def cbslah(z):
    _H[0] = sla(memory.peekb(z))
    memory.pokeb(z, _H[0])
    return 23


def cbslal(z):
    _L[0] = sla(memory.peekb(z))
    memory.pokeb(z, _L[0])
    return 23


def cbslainhl(z):
    memory.pokeb(z, sla(memory.peekb(z)))
    return 23


def cbslaa(z):
    _A[0] = sla(memory.peekb(z))
    memory.pokeb(z, _A[0])
    return 23


# SRA *
def cbsrab(z):
    _B[0] = sra(memory.peekb(z))
    memory.pokeb(z, _B[0])
    return 23

def cbsrac(z):
    _C[0] = sra(memory.peekb(z))
    memory.pokeb(z, _C[0])
    return 23


def cbsrad(z):
    _D[0] = sra(memory.peekb(z))
    memory.pokeb(z, _D[0])
    return 23


def cbsrae(z):
    _E[0] = sra(memory.peekb(z))
    memory.pokeb(z, _E[0])
    return 23


def cbsrah(z):
    _H[0] = sra(memory.peekb(z))
    memory.pokeb(z, _H[0])
    return 23


def cbsral(z):
    _L[0] = sra(memory.peekb(z))
    memory.pokeb(z, _L[0])
    return 23


def cbsrainhl(z):
    memory.pokeb(z, sra(memory.peekb(z)))
    return 23


def cbsraa(z):
    _A[0] = sra(memory.peekb(z))
    memory.pokeb(z, _A[0])
    return 23


# SLS *
def cbslsb(z):
    _B[0] = sls(memory.peekb(z))
    memory.pokeb(z, _B[0])
    return 23

def cbslsc(z):
    _C[0] = sls(memory.peekb(z))
    memory.pokeb(z, _C[0])
    return 23


def cbslsd(z):
    _D[0] = sls(memory.peekb(z))
    memory.pokeb(z, _D[0])
    return 23


def cbslse(z):
    _E[0] = sls(memory.peekb(z))
    memory.pokeb(z, _E[0])
    return 23


def cbslsh(z):
    _H[0] = sls(memory.peekb(z))
    memory.pokeb(z, _H[0])
    return 23


def cbslsl(z):
    _L[0] = sls(memory.peekb(z))
    memory.pokeb(z, _L[0])
    return 23


def cbslsinhl(z):
    memory.pokeb(z, sls(memory.peekb(z)))
    return 23


def cbslsa(z):
    _A[0] = sls(memory.peekb(z))
    memory.pokeb(z, _A[0])
    return 23


# SRL *
def cbsrlb(z):
    _B[0] = srl(memory.peekb(z))
    memory.pokeb(z, _B[0])
    return 23

def cbsrlc(z):
    _C[0] = srl(memory.peekb(z))
    memory.pokeb(z, _C[0])
    return 23


def cbsrld(z):
    _D[0] = srl(memory.peekb(z))
    memory.pokeb(z, _D[0])
    return 23


def cbsrle(z):
    _E[0] = srl(memory.peekb(z))
    memory.pokeb(z, _E[0])
    return 23


def cbsrlh(z):
    _H[0] = srl(memory.peekb(z))
    memory.pokeb(z, _H[0])
    return 23


def cbsrll(z):
    _L[0] = srl(memory.peekb(z))
    memory.pokeb(z, _L[0])
    return 23


def cbsrlinhl(z):
    memory.pokeb(z, srl(memory.peekb(z)))
    return 23


def cbsrla(z):
    _A[0] = srl(memory.peekb(z))
    memory.pokeb(z, _A[0])
    return 23


# BIT *
def cbbit0(z):
    bit(0x01, memory.peekb(z))
    return 20


def cbbit1(z):
    bit(0x02, memory.peekb(z))
    return 20


def cbbit2(z):
    bit(0x04, memory.peekb(z))
    return 20


def cbbit3(z):
    bit(0x08, memory.peekb(z))
    return 20


def cbbit4(z):
    bit(0x10, memory.peekb(z))
    return 20


def cbbit5(z):
    bit(0x20, memory.peekb(z))
    return 20


def cbbit6(z):
    bit(0x40, memory.peekb(z))
    return 20


def cbbit7(z):
    bit(0x80, memory.peekb(z))
    return 20


# RES 0, *
def cbres0b(z):
    _B[0] = res(0x01, memory.peekb(z))
    memory.pokeb(z, _B[0])
    return 23


def cbres0c(z):
    _C[0] = res(0x01, memory.peekb(z))
    memory.pokeb(z, _C[0])
    return 23


def cbres0d(z):
    _D[0] = res(0x01, memory.peekb(z))
    memory.pokeb(z, _D[0])
    return 23


def cbres0e(z):
    _E[0] = res(0x01, memory.peekb(z))
    memory.pokeb(z, _E[0])
    return 23


def cbres0h(z):
    _H[0] = res(0x01, memory.peekb(z))
    memory.pokeb(z, _H[0])
    return 23


def cbres0l(z):
    _L[0] = res(0x01, memory.peekb(z))
    memory.pokeb(z, _L[0])
    return 23


def cbres0inhl(z):
    memory.pokeb(z, res(0x01, memory.peekb(z)))
    return 23


def cbres0a(z):
    _A[0] = res(0x01, memory.peekb(z))
    memory.pokeb(z, _A[0])
    return 23


# RES 1, *
def cbres1b(z):
    _B[0] = res(0x02, memory.peekb(z))
    memory.pokeb(z, _B[0])
    return 23


def cbres1c(z):
    _C[0] = res(0x02, memory.peekb(z))
    memory.pokeb(z, _C[0])
    return 23


def cbres1d(z):
    _D[0] = res(0x02, memory.peekb(z))
    memory.pokeb(z, _D[0])
    return 23


def cbres1e(z):
    _E[0] = res(0x02, memory.peekb(z))
    memory.pokeb(z, _E[0])
    return 23


def cbres1h(z):
    _H[0] = res(0x02, memory.peekb(z))
    memory.pokeb(z, _H[0])
    return 23


def cbres1l(z):
    _L[0] = res(0x02, memory.peekb(z))
    memory.pokeb(z, _L[0])
    return 23


def cbres1inhl(z):
    memory.pokeb(z, res(0x02, memory.peekb(z)))
    return 23


def cbres1a(z):
    _A[0] = res(0x02, memory.peekb(z))
    memory.pokeb(z, _A[0])
    return 23


# RES 2, *
def cbres2b(z):
    _B[0] = res(0x04, memory.peekb(z))
    memory.pokeb(z, _B[0])
    return 23


def cbres2c(z):
    _C[0] = res(0x04, memory.peekb(z))
    memory.pokeb(z, _C[0])
    return 23


def cbres2d(z):
    _D[0] = res(0x04, memory.peekb(z))
    memory.pokeb(z, _D[0])
    return 23


def cbres2e(z):
    _E[0] = res(0x04, memory.peekb(z))
    memory.pokeb(z, _E[0])
    return 23


def cbres2h(z):
    _H[0] = res(0x04, memory.peekb(z))
    memory.pokeb(z, _H[0])
    return 23


def cbres2l(z):
    _L[0] = res(0x04, memory.peekb(z))
    memory.pokeb(z, _L[0])
    return 23


def cbres2inhl(z):
    memory.pokeb(z, res(0x04, memory.peekb(z)))
    return 23


def cbres2a(z):
    _A[0] = res(0x04, memory.peekb(z))
    memory.pokeb(z, _A[0])
    return 23


# RES 3, *
def cbres3b(z):
    _B[0] = res(0x08, memory.peekb(z))
    memory.pokeb(z, _B[0])
    return 23


def cbres3c(z):
    _C[0] = res(0x08, memory.peekb(z))
    memory.pokeb(z, _C[0])
    return 23


def cbres3d(z):
    _D[0] = res(0x08, memory.peekb(z))
    memory.pokeb(z, _D[0])
    return 23


def cbres3e(z):
    _E[0] = res(0x08, memory.peekb(z))
    memory.pokeb(z, _E[0])
    return 23


def cbres3h(z):
    _H[0] = res(0x08, memory.peekb(z))
    memory.pokeb(z, _H[0])
    return 23


def cbres3l(z):
    _L[0] = res(0x08, memory.peekb(z))
    memory.pokeb(z, _L[0])
    return 23


def cbres3inhl(z):
    memory.pokeb(z, res(0x08, memory.peekb(z)))
    return 23


def cbres3a(z):
    _A[0] = res(0x08, memory.peekb(z))
    memory.pokeb(z, _A[0])
    return 23


# RES 4, *
def cbres4b(z):
    _B[0] = res(0x10, memory.peekb(z))
    memory.pokeb(z, _B[0])
    return 23


def cbres4c(z):
    _C[0] = res(0x10, memory.peekb(z))
    memory.pokeb(z, _C[0])
    return 23


def cbres4d(z):
    _D[0] = res(0x10, memory.peekb(z))
    memory.pokeb(z, _D[0])
    return 23


def cbres4e(z):
    _E[0] = res(0x10, memory.peekb(z))
    memory.pokeb(z, _E[0])
    return 23


def cbres4h(z):
    _H[0] = res(0x10, memory.peekb(z))
    memory.pokeb(z, _H[0])
    return 23


def cbres4l(z):
    _L[0] = res(0x10, memory.peekb(z))
    memory.pokeb(z, _L[0])
    return 23


def cbres4inhl(z):
    memory.pokeb(z, res(0x10, memory.peekb(z)))
    return 23


def cbres4a(z):
    _A[0] = res(0x10, memory.peekb(z))
    memory.pokeb(z, _A[0])
    return 23


# RES 5, *
def cbres5b(z):
    _B[0] = res(0x20, memory.peekb(z))
    memory.pokeb(z, _B[0])
    return 23


def cbres5c(z):
    _C[0] = res(0x20, memory.peekb(z))
    memory.pokeb(z, _C[0])
    return 23


def cbres5d(z):
    _D[0] = res(0x20, memory.peekb(z))
    memory.pokeb(z, _D[0])
    return 23


def cbres5e(z):
    _E[0] = res(0x20, memory.peekb(z))
    memory.pokeb(z, _E[0])
    return 23


def cbres5h(z):
    _H[0] = res(0x20, memory.peekb(z))
    memory.pokeb(z, _H[0])
    return 23


def cbres5l(z):
    _L[0] = res(0x20, memory.peekb(z))
    memory.pokeb(z, _L[0])
    return 23


def cbres5inhl(z):
    memory.pokeb(z, res(0x20, memory.peekb(z)))
    return 23


def cbres5a(z):
    _A[0] = res(0x20, memory.peekb(z))
    memory.pokeb(z, _A[0])
    return 23


# RES 6, *
def cbres6b(z):
    _B[0] = res(0x40, memory.peekb(z))
    memory.pokeb(z, _B[0])
    return 23


def cbres6c(z):
    _C[0] = res(0x40, memory.peekb(z))
    memory.pokeb(z, _C[0])
    return 23


def cbres6d(z):
    _D[0] = res(0x40, memory.peekb(z))
    memory.pokeb(z, _D[0])
    return 23


def cbres6e(z):
    _E[0] = res(0x40, memory.peekb(z))
    memory.pokeb(z, _E[0])
    return 23


def cbres6h(z):
    _H[0] = res(0x40, memory.peekb(z))
    memory.pokeb(z, _H[0])
    return 23


def cbres6l(z):
    _L[0] = res(0x40, memory.peekb(z))
    memory.pokeb(z, _L[0])
    return 23


def cbres6inhl(z):
    memory.pokeb(z, res(0x40, memory.peekb(z)))
    return 23


def cbres6a(z):
    _A[0] = res(0x40, memory.peekb(z))
    memory.pokeb(z, _A[0])
    return 23


# RES 7, *
def cbres7b(z):
    _B[0] = res(0x80, memory.peekb(z))
    memory.pokeb(z, _B[0])
    return 23


def cbres7c(z):
    _C[0] = res(0x80, memory.peekb(z))
    memory.pokeb(z, _C[0])
    return 23


def cbres7d(z):
    _D[0] = res(0x80, memory.peekb(z))
    memory.pokeb(z, _D[0])
    return 23


def cbres7e(z):
    _E[0] = res(0x80, memory.peekb(z))
    memory.pokeb(z, _E[0])
    return 23


def cbres7h(z):
    _H[0] = res(0x80, memory.peekb(z))
    memory.pokeb(z, _H[0])
    return 23


def cbres7l(z):
    _L[0] = res(0x80, memory.peekb(z))
    memory.pokeb(z, _L[0])
    return 23


def cbres7inhl(z):
    memory.pokeb(z, res(0x80, memory.peekb(z)))
    return 23


def cbres7a(z):
    _A[0] = res(0x80, memory.peekb(z))
    memory.pokeb(z, _A[0])
    return 23


# SET 0, *
def cbset0b(z):
    _B[0] = set(0x01, memory.peekb(z))
    memory.pokeb(z, _B[0])
    return 23


def cbset0c(z):
    _C[0] = set(0x01, memory.peekb(z))
    memory.pokeb(z, _C[0])
    return 23


def cbset0d(z):
    _D[0] = set(0x01, memory.peekb(z))
    memory.pokeb(z, _D[0])
    return 23


def cbset0e(z):
    _E[0] = set(0x01, memory.peekb(z))
    memory.pokeb(z, _E[0])
    return 23


def cbset0h(z):
    _H[0] = set(0x01, memory.peekb(z))
    memory.pokeb(z, _H[0])
    return 23


def cbset0l(z):
    _L[0] = set(0x01, memory.peekb(z))
    memory.pokeb(z, _L[0])
    return 23


def cbset0inhl(z):
    memory.pokeb(z, set(0x01, memory.peekb(z)))
    return 23


def cbset0a(z):
    _A[0] = set(0x01, memory.peekb(z))
    memory.pokeb(z, _A[0])
    return 23


# SET 1, *
def cbset1b(z):
    _B[0] = set(0x02, memory.peekb(z))
    memory.pokeb(z, _B[0])
    return 23


def cbset1c(z):
    _C[0] = set(0x02, memory.peekb(z))
    memory.pokeb(z, _C[0])
    return 23


def cbset1d(z):
    _D[0] = set(0x02, memory.peekb(z))
    memory.pokeb(z, _D[0])
    return 23


def cbset1e(z):
    _E[0] = set(0x02, memory.peekb(z))
    memory.pokeb(z, _E[0])
    return 23


def cbset1h(z):
    _H[0] = set(0x02, memory.peekb(z))
    memory.pokeb(z, _H[0])
    return 23


def cbset1l(z):
    _L[0] = set(0x02, memory.peekb(z))
    memory.pokeb(z, _L[0])
    return 23


def cbset1inhl(z):
    memory.pokeb(z, set(0x02, memory.peekb(z)))
    return 23


def cbset1a(z):
    _A[0] = set(0x02, memory.peekb(z))
    memory.pokeb(z, _A[0])
    return 23


# SET 2, *
def cbset2b(z):
    _B[0] = set(0x04, memory.peekb(z))
    memory.pokeb(z, _B[0])
    return 23


def cbset2c(z):
    _C[0] = set(0x04, memory.peekb(z))
    memory.pokeb(z, _C[0])
    return 23


def cbset2d(z):
    _D[0] = set(0x04, memory.peekb(z))
    memory.pokeb(z, _D[0])
    return 23


def cbset2e(z):
    _E[0] = set(0x04, memory.peekb(z))
    memory.pokeb(z, _E[0])
    return 23


def cbset2h(z):
    _H[0] = set(0x04, memory.peekb(z))
    memory.pokeb(z, _H[0])
    return 23


def cbset2l(z):
    _L[0] = set(0x04, memory.peekb(z))
    memory.pokeb(z, _L[0])
    return 23


def cbset2inhl(z):
    memory.pokeb(z, set(0x04, memory.peekb(z)))
    return 23


def cbset2a(z):
    _A[0] = set(0x04, memory.peekb(z))
    memory.pokeb(z, _A[0])
    return 23


# SET 3, *
def cbset3b(z):
    _B[0] = set(0x08, memory.peekb(z))
    memory.pokeb(z, _B[0])
    return 23


def cbset3c(z):
    _C[0] = set(0x08, memory.peekb(z))
    memory.pokeb(z, _C[0])
    return 23


def cbset3d(z):
    _D[0] = set(0x08, memory.peekb(z))
    memory.pokeb(z, _D[0])
    return 23


def cbset3e(z):
    _E[0] = set(0x08, memory.peekb(z))
    memory.pokeb(z, _E[0])
    return 23


def cbset3h(z):
    _H[0] = set(0x08, memory.peekb(z))
    memory.pokeb(z, _H[0])
    return 23


def cbset3l(z):
    _L[0] = set(0x08, memory.peekb(z))
    memory.pokeb(z, _L[0])
    return 23


def cbset3inhl(z):
    memory.pokeb(z, set(0x08, memory.peekb(z)))
    return 23


def cbset3a(z):
    _A[0] = set(0x08, memory.peekb(z))
    memory.pokeb(z, _A[0])
    return 23


# SET 4, *
def cbset4b(z):
    _B[0] = set(0x10, memory.peekb(z))
    memory.pokeb(z, _B[0])
    return 23


def cbset4c(z):
    _C[0] = set(0x10, memory.peekb(z))
    memory.pokeb(z, _C[0])
    return 23


def cbset4d(z):
    _D[0] = set(0x10, memory.peekb(z))
    memory.pokeb(z, _D[0])
    return 23


def cbset4e(z):
    _E[0] = set(0x10, memory.peekb(z))
    memory.pokeb(z, _E[0])
    return 23


def cbset4h(z):
    _H[0] = set(0x10, memory.peekb(z))
    memory.pokeb(z, _H[0])
    return 23


def cbset4l(z):
    _L[0] = set(0x10, memory.peekb(z))
    memory.pokeb(z, _L[0])
    return 23


def cbset4inhl(z):
    memory.pokeb(z, set(0x10, memory.peekb(z)))
    return 23


def cbset4a(z):
    _A[0] = set(0x10, memory.peekb(z))
    memory.pokeb(z, _A[0])
    return 23


# SET 5, *
def cbset5b(z):
    _B[0] = set(0x20, memory.peekb(z))
    memory.pokeb(z, _B[0])
    return 23


def cbset5c(z):
    _C[0] = set(0x20, memory.peekb(z))
    memory.pokeb(z, _C[0])
    return 23


def cbset5d(z):
    _D[0] = set(0x20, memory.peekb(z))
    memory.pokeb(z, _D[0])
    return 23


def cbset5e(z):
    _E[0] = set(0x20, memory.peekb(z))
    memory.pokeb(z, _E[0])
    return 23


def cbset5h(z):
    _H[0] = set(0x20, memory.peekb(z))
    memory.pokeb(z, _H[0])
    return 23


def cbset5l(z):
    _L[0] = set(0x20, memory.peekb(z))
    memory.pokeb(z, _L[0])
    return 23


def cbset5inhl(z):
    memory.pokeb(z, set(0x20, memory.peekb(z)))
    return 23


def cbset5a(z):
    _A[0] = set(0x20, memory.peekb(z))
    memory.pokeb(z, _A[0])
    return 23


# SET 6, *
def cbset6b(z):
    _B[0] = set(0x40, memory.peekb(z))
    memory.pokeb(z, _B[0])
    return 23


def cbset6c(z):
    _C[0] = set(0x40, memory.peekb(z))
    memory.pokeb(z, _C[0])
    return 23


def cbset6d(z):
    _D[0] = set(0x40, memory.peekb(z))
    memory.pokeb(z, _D[0])
    return 23


def cbset6e(z):
    _E[0] = set(0x40, memory.peekb(z))
    memory.pokeb(z, _E[0])
    return 23


def cbset6h(z):
    _H[0] = set(0x40, memory.peekb(z))
    memory.pokeb(z, _H[0])
    return 23


def cbset6l(z):
    _L[0] = set(0x40, memory.peekb(z))
    memory.pokeb(z, _L[0])
    return 23


def cbset6inhl(z):
    memory.pokeb(z, set(0x40, memory.peekb(z)))
    return 23


def cbset6a(z):
    _A[0] = set(0x40, memory.peekb(z))
    memory.pokeb(z, _A[0])
    return 23


# SET 7, *
def cbset7b(z):
    _B[0] = set(0x80, memory.peekb(z))
    memory.pokeb(z, _B[0])
    return 23


def cbset7c(z):
    _C[0] = set(0x80, memory.peekb(z))
    memory.pokeb(z, _C[0])
    return 23


def cbset7d(z):
    _D[0] = set(0x80, memory.peekb(z))
    memory.pokeb(z, _D[0])
    return 23


def cbset7e(z):
    _E[0] = set(0x80, memory.peekb(z))
    memory.pokeb(z, _E[0])
    return 23


def cbset7h(z):
    _H[0] = set(0x80, memory.peekb(z))
    memory.pokeb(z, _H[0])
    return 23


def cbset7l(z):
    _L[0] = set(0x80, memory.peekb(z))
    memory.pokeb(z, _L[0])
    return 23


def cbset7inhl(z):
    memory.pokeb(z, set(0x80, memory.peekb(z)))
    return 23


def cbset7a(z):
    _A[0] = set(0x80, memory.peekb(z))
    memory.pokeb(z, _A[0])
    return 23


_idcbdict = {
    0: cbrlcb, 1: cbrlcc, 2: cbrlcd, 3: cbrlce, 4: cbrlch, 5: cbrlcl, 6: cbrlcinhl, 7: cbrlca,
    8: cbrrcb, 9: cbrrcc, 10: cbrrcd, 11: cbrrce, 12: cbrrch, 13: cbrrcl, 14: cbrrcinhl, 15: cbrrca,
    16: cbrlb, 17: cbrlc, 18: cbrld, 19: cbrle, 20: cbrlh, 21: cbrll, 22: cbrlinhl, 23: cbrla,
    24: cbrrb, 25: cbrrc, 26: cbrrd, 27: cbrre, 28: cbrrh, 29: cbrrl, 30: cbrrinhl, 31: cbrra,
    32: cbslab, 33: cbslac, 34: cbslad, 35: cbslae, 36: cbslah, 37: cbslal, 38: cbslainhl, 39: cbslaa,
    40: cbsrab, 41: cbsrac, 42: cbsrad, 43: cbsrae, 44: cbsrah, 45: cbsral, 46: cbsrainhl, 47: cbsraa,
    48: cbslsb, 49: cbslsc, 50: cbslsd, 51: cbslse, 52: cbslsh, 53: cbslsl, 54: cbslsinhl, 55: cbslsa,
    56: cbsrlb, 57: cbsrlc, 58: cbsrld, 59: cbsrle, 60: cbsrlh, 61: cbsrll, 62: cbsrlinhl, 63: cbsrla,
    64: cbbit0, 65: cbbit0, 66: cbbit0, 67: cbbit0, 68: cbbit0, 69: cbbit0, 70: cbbit0, 71: cbbit0,
    72: cbbit1, 73: cbbit1, 74: cbbit1, 75: cbbit1, 76: cbbit1, 77: cbbit1, 78: cbbit1, 79: cbbit1,
    80: cbbit2, 81: cbbit2, 82: cbbit2, 83: cbbit2, 84: cbbit2, 85: cbbit2, 86: cbbit2, 87: cbbit2,
    88: cbbit3, 89: cbbit3, 90: cbbit3, 91: cbbit3, 92: cbbit3, 93: cbbit3, 94: cbbit3, 95: cbbit3,
    96: cbbit4, 97: cbbit4, 98: cbbit4, 99: cbbit4, 100: cbbit4, 101: cbbit4, 102: cbbit4, 103: cbbit4,
    104: cbbit5, 105: cbbit5, 106: cbbit5, 107: cbbit5, 108: cbbit5, 109: cbbit5, 110: cbbit5, 111: cbbit5,
    112: cbbit6, 113: cbbit6, 114: cbbit6, 115: cbbit6, 116: cbbit6, 117: cbbit6, 118: cbbit6, 119: cbbit6,
    120: cbbit7, 121: cbbit7, 122: cbbit7, 123: cbbit7, 124: cbbit7, 125: cbbit7, 126: cbbit7, 127: cbbit7,
    128: cbres0b, 129: cbres0c, 130: cbres0d, 131: cbres0e, 132: cbres0h, 133: cbres0l, 134: cbres0inhl, 135: cbres0a,
    136: cbres1b, 137: cbres1c, 138: cbres1d, 139: cbres1e, 140: cbres1h, 141: cbres1l, 142: cbres1inhl, 143: cbres1a,
    144: cbres2b, 145: cbres2c, 146: cbres2d, 147: cbres2e, 148: cbres2h, 149: cbres2l, 150: cbres2inhl, 151: cbres2a,
    152: cbres3b, 153: cbres3c, 154: cbres3d, 155: cbres3e, 156: cbres3h, 157: cbres3l, 158: cbres3inhl, 159: cbres3a,
    160: cbres4b, 161: cbres4c, 162: cbres4d, 163: cbres4e, 164: cbres4h, 165: cbres4l, 166: cbres4inhl, 167: cbres4a,
    168: cbres5b, 169: cbres5c, 170: cbres5d, 171: cbres5e, 172: cbres5h, 173: cbres5l, 174: cbres5inhl, 175: cbres5a,
    176: cbres6b, 177: cbres6c, 178: cbres6d, 179: cbres6e, 180: cbres6h, 181: cbres6l, 182: cbres6inhl, 183: cbres6a,
    184: cbres7b, 185: cbres7c, 186: cbres7d, 187: cbres7e, 188: cbres7h, 189: cbres7l, 190: cbres7inhl, 191: cbres7a,
    192: cbset0b, 193: cbset0c, 194: cbset0d, 195: cbset0e, 196: cbset0h, 197: cbset0l, 198: cbset0inhl, 199: cbset0a,
    200: cbset1b, 201: cbset1c, 202: cbset1d, 203: cbset1e, 204: cbset1h, 205: cbset1l, 206: cbset1inhl, 207: cbset1a,
    208: cbset2b, 209: cbset2c, 210: cbset2d, 211: cbset2e, 212: cbset2h, 213: cbset2l, 214: cbset2inhl, 215: cbset2a,
    216: cbset3b, 217: cbset3c, 218: cbset3d, 219: cbset3e, 220: cbset3h, 221: cbset3l, 222: cbset3inhl, 223: cbset3a,
    224: cbset4b, 225: cbset4c, 226: cbset4d, 227: cbset4e, 228: cbset4h, 229: cbset4l, 230: cbset4inhl, 231: cbset4a,
    232: cbset5b, 233: cbset5c, 234: cbset5d, 235: cbset5e, 236: cbset5h, 237: cbset5l, 238: cbset5inhl, 239: cbset5a,
    240: cbset6b, 241: cbset6c, 242: cbset6d, 243: cbset6e, 244: cbset6h, 245: cbset6l, 246: cbset6inhl, 247: cbset6a,
    248: cbset7b, 249: cbset7c, 250: cbset7d, 251: cbset7e, 252: cbset7h, 253: cbset7l, 254: cbset7inhl, 255: cbset7a
}


def in_bc():
    global _fS, _f3, _f5, _fZ, _fPV, _fH, _fN
    ans = ports.port_in(_BC[0])
    _fZ = ans == 0
    _fS = ans > 0x7f
    _f3 = (ans & F_3) != 0
    _f5 = (ans & F_5) != 0
    _fPV = parity[ans]
    _fN = False
    _fH = False
    return ans


"""
The algorithm for calculating P/V flag for ADD instruction is: 
if (((reg_a ^ operand) & 0x80) == 0 /* Same sign */
&& ((reg_a ^ result) & 0x80) != 0) /* Not same sign */
overflow = 1;
else
overflow = 0;
"""
# Add with carry - alters all flags (CHECKED)
def adc_a(b):
    global _fS, _f3, _f5, _fZ, _fC, _fPV, _fH, _fN
    a = _A[0]
    c = 1 if _fC else 0
    ans = (a + b + c) % 256
    _fS = ans > 0x7f
    _f3 = (ans & F_3) != 0
    _f5 = (ans & F_5) != 0
    _fZ  = not ans
    _fC = a > ans
    _fPV = ((a ^ b) < 0x80) and ((a ^ ans) > 0x7f)
    # _fH = ((ans ^ a ^ b) & 0x10) != 0
    _fH = ((a % 16) + (b % 16) + c) > 0x0f
    _fN = False
    _A[0] = ans


# Add - alters all flags (CHECKED)
def add_a(b):
    global _fS, _f3, _f5, _fZ, _fC, _fPV, _fH, _fN
    a = _A[0]
    ans = (a + b) % 256
    _fS = ans > 0x7f
    _f3 = (ans & F_3) != 0
    _f5 = (ans & F_5) != 0
    _fZ  = not ans
    _fC = a > ans
    _fPV = ((a ^ b) < 0x80) and ((a ^ ans) > 0x7f)
    _fH = ((a % 16) + (b % 16)) > 0x0f
    _fN = False
    _A[0] = ans


# print 'add_a(%d): a=%d wans=%d ans=%d' % (b, a, wans, ans)

"""
While for SUB instruction is:

if (((reg_a ^ operand) & 0x80) != 0 /* Not same sign */
&& ((operand ^ result) & 0x80) == 0) /* Same sign */
overflow = 1;
else
overflow = 0; 
"""
# Subtract with carry - alters all flags (CHECKED)
def sbc_a(b):
    global _fS, _f3, _f5, _fZ, _fC, _fPV, _fH, _fN
    a = _A[0]
    c = 1 if _fC else 0
    ans = (a - b - c) % 256
    _fS = ans > 0x7f
    _f3 = (ans & F_3) != 0
    _f5 = (ans & F_5) != 0
    _fZ  = not ans
    _fC = a < ans
    _fPV = ((a ^ b) > 0x7f) and ((b ^ ans) < 0x80)
    _fH = ((a % 16) - (b % 16) - c) < 0
    _fN = True
    _A[0] = ans


# Subtract - alters all flags (CHECKED)
def sub_a(b):
    global _fS, _f3, _f5, _fZ, _fC, _fPV, _fH, _fN
    a = _A[0]
    ans = (a - b) % 256
    _fS = ans > 0x7f
    _f3 = (ans & F_3) != 0
    _f5 = (ans & F_5) != 0
    _fZ  = not ans
    _fC = a < ans
    _fPV = ((a ^ b) > 0x7f) and ((b ^ ans) < 0x80)
    _fH = ((a % 16) - (b % 16)) < 0
    _fN = True
    _A[0] = ans


# Increment - alters all but C flag (CHECKED)
def inc8(ans):
    global _fS, _f3, _f5, _fN, _fZ, _fH, _fPV
    ans = (ans + 1) % 256
    _fS = ans > 0x7f
    _f3 = (ans & F_3) != 0
    _f5 = (ans & F_5) != 0
    _fZ = not ans
    _fPV = ans == 0x80
    _fH = not (ans % 16)
    _fN = False
    return ans


# Decrement - alters all but C flag (CHECKED)
def dec8(ans):
    global _fS, _f3, _f5, _fN, _fZ, _fH, _fPV
    h = not (ans % 16)
    ans = (ans - 1) %256
    _fS = ans > 0x7f
    _f3 = (ans & F_3) != 0
    _f5 = (ans & F_5) != 0
    _fZ = not ans
    _fPV = ans == 0x7f
    _fH = h
    _fN = True
    return ans

# Add with carry - (NOT CHECKED)
def adc16(a, b):
    global _fS, _f3, _f5, _fN, _fZ, _fC, _fH, _fPV
    print(f'_fC = {_fC}, a = 0x{a:4x}, b = 0x{b:4x}')
    c = 1 if _fC else 0
    ans = (a + b + c) % 65536
    _fS = ans > 0x7fff
    _f3 = (ans & F_3_16) != 0 
    _f5 = (ans & F_5_16) != 0
    _fZ = not ans
    _fC = a > ans
    _fPV = ((a ^ b) < 0x8000) and ((a ^ ans) > 0x7fff)
    _fH = ((a % 0x1000) + (b % 0x1000) + c) > 0x0fff
    _fH = ((ans ^ a ^ b) & 0x1000) != 0
    _fN = False
    return ans


# Add - (NOT CHECKED)
def add16(a, b):
    global _f3, _f5, _fC, _fH
    ans = (a + b) % 65536
    _f3 = (ans & F_3_16) != 0 
    _f5 = (ans & F_5_16) != 0
    _fC = a > ans
    _fH = ((a % 0x1000) + (b % 0x1000)) > 0x0fff
    return ans


# Add with carry - (NOT CHECKED)
def sbc16(a, b):
    global _fS, _f3, _f5, _fN, _fZ, _fC, _fH
    c = 1 if _fC else 0
    ans = (a - b - c) % 65536
    _fS = ans > 0x7fff
    _f3 = (ans & F_3_16) != 0 
    _f5 = (ans & F_5_16) != 0
    _fZ = not ans
    _fC = a < ans
    _fPV = ((a ^ b) > 0x7fff) and ((b ^ ans) < 0x8000)
    _fH = ((a % 0x1000) - (b % 0x1000) - c) < 0
    _fN = True
    return ans


# TODO: check comparisons !
# Compare - alters all flags (CHECKED)
def cp_a(b):
    global _fS, _f3, _f5, _fN, _fZ, _fC, _fH, _fPV
    a = _A[0]
    ans = (a - b) % 256
    _fS = ans > 0x7f
    _f3 = (ans & F_3) != 0
    _f5 = (ans & F_5) != 0
    _fZ  = not ans
    _fC = a < ans
    _fPV = ((a ^ b) > 0x7f) and ((b ^ ans) < 0x80)
    _fH = ((a % 16) - (b % 16)) < 0
    _fN = True


# Bitwise and - alters all flags (CHECKED)
def and_a(b):
    global _fS, _f3, _f5, _fN, _fZ, _fC, _fH, _fPV
    ans = _A[0] & b
    _fS = ans > 0x7f
    _f3 = (ans & F_3) != 0
    _f5 = (ans & F_5) != 0
    _fH = True
    _fPV = parity[ans]
    _fZ = not ans
    _fN = False
    _fC = False
    _A[0] = ans


# Bitwise or - alters all flags (CHECKED)
def or_a(b):
    global _fS, _f3, _f5, _fN, _fZ, _fC, _fH, _fPV
    ans = _A[0] | b
    _fS = ans > 0x7f
    _f3 = (ans & F_3) != 0
    _f5 = (ans & F_5) != 0
    _fH = False
    _fPV = parity[ans]
    _fZ = not ans
    _fN = False
    _fC = False
    _A[0] = ans


# Bitwise exclusive or - alters all flags (CHECKED)
def xor_a(b):
    global _fS, _f3, _f5, _fN, _fZ, _fC, _fH, _fPV
    ans = (_A[0] ^ b) % 256
    _fS = ans > 0x7f
    _f3 = (ans & F_3) != 0
    _f5 = (ans & F_5) != 0
    _fH = False
    _fPV = parity[ans]
    _fZ = not ans
    _fN = False
    _fC = False
    _A[0] = ans


# Test bit - alters all but C flag (CHECKED)
def bit(b, r):
    global _fS, _f3, _f5, _fN, _fZ, _fC, _fH, _fPV
    bitset = (r & b) != 0
    _fS = bitset if b == F_S else False
    _f3 = (r & F_3) != 0
    _f5 = (r & F_5) != 0
    _fN = False
    _fH = True
    _fZ = not bitset
    _fPV = _fZ


# Rotate left - alters all flags (CHECKED)
def rlc(ans):
    global _f3, _f5, _fN, _fH, _fC, _fPV, _fZ, _fS
    c = ans > 0x7f
    ans = ((ans << 1) + (0x01 if c else 0)) % 256
    _fS = ans > 0x7f
    _f3 = (ans & F_3) != 0
    _f5 = (ans & F_5) != 0
    _fPV = parity[ans]
    _fZ = not ans
    _fN = False
    _fH = False
    _fC = c
    return ans


# Rotate left through carry - alters all flags (CHECKED)
def rl(ans):
    global _f3, _f5, _fN, _fH, _fC, _fPV, _fZ, _fS
    c = ans > 0x7F
    ans = ((ans << 1) + (1 if _fC else 0)) % 256
    _fS = ans > 0x7f
    _f3 = (ans & F_3) != 0
    _f5 = (ans & F_5) != 0
    _fPV = parity[ans]
    _fZ = not ans
    _fN = False
    _fH = False
    _fC = c
    return ans


# Rotate right - alters all flags (CHECKED)
def rrc(ans):
    global _f3, _f5, _fN, _fH, _fC, _fPV, _fZ, _fS
    c = (ans % 2) != 0
    ans = ((ans >> 1) + (0x80 if c else 0)) % 256
    _fS = ans > 0x7f
    _f3 = (ans & F_3) != 0
    _f5 = (ans & F_5) != 0
    _fPV = parity[ans]
    _fZ = not ans
    _fN = False
    _fH = False
    _fC = c
    return ans


# Rotate right through carry - alters all flags (CHECKED)
def rr(ans):
    global _f3, _f5, _fN, _fH, _fC, _fPV, _fZ, _fS
    c = (ans % 2) != 0
    ans = ((ans >> 1) + (0x80 if _fC else 0)) % 256
    _fS = ans > 0x7f
    _f3 = (ans & F_3) != 0
    _f5 = (ans & F_5) != 0
    _fPV = parity[ans]
    _fZ = not ans
    _fN = False
    _fH = False
    _fC = c
    return ans


# Shift Left Arithmetically - alters all flags (CHECKED)
def sla(ans):
    global _f3, _f5, _fN, _fH, _fC, _fPV, _fZ, _fS
    c = ans > 0x7f
    ans = (ans << 1) % 256
    _fS = ans > 0x7f
    _f3 = (ans & F_3) != 0
    _f5 = (ans & F_5) != 0
    _fPV = parity[ans]
    _fZ = not ans
    _fN = False
    _fH = False
    _fC = c
    return ans


# Shift Right Arithmetically - alters all flags (CHECKED)
def sra(ans):
    global _f3, _f5, _fN, _fH, _fC, _fPV, _fZ, _fS
    c = (ans % 2) != 0
    b7 = 0x80 if ans > 0x7f else 0 
    ans = ((ans >> 1) + b7) % 256
    _fS = ans > 0x7f
    _f3 = (ans & F_3) != 0
    _f5 = (ans & F_5) != 0
    _fPV = parity[ans]
    _fZ = not ans
    _fN = False
    _fH = False
    _fC = c
    return ans


# Shift Right Logically - alters all flags (CHECKED)
def srl(ans):
    global _f3, _f5, _fN, _fH, _fC, _fPV, _fZ, _fS
    c = (ans % 2) != 0
    ans = (ans >> 1) % 256
    _fS = ans > 0x7f
    _f3 = (ans & F_3) != 0
    _f5 = (ans & F_5) != 0
    _fPV = parity[ans]
    _fZ = not ans
    _fN = False
    _fH = False
    _fC = c
    return ans


# Shift Left and Set - alters all flags (CHECKED)
def sls(ans):
    global _f3, _f5, _fN, _fH, _fC, _fPV, _fZ, _fS
    c = ans > 0x7f
    ans = ((ans << 1) + 1) % 256
    _fS = ans > 0x7f
    _f3 = (ans & F_3) != 0
    _f5 = (ans & F_5) != 0
    _fPV = parity[ans]
    _fZ = not ans
    _fN = False
    _fH = False
    _fC = c
    return ans


# Quick Increment : no flags
def inc16(a):
    return (a + 1) % 65536


def qinc8(a):
    return (a + 1) % 256


# Quick Decrement : no flags
def dec16(a):
    return (a - 1) % 65536


def qdec8(a):
    return (a - 1) % 256


# Bit toggling
def res(bit, val): 
    return val & ~bit


def set(bit, val): 
    return val | bit
