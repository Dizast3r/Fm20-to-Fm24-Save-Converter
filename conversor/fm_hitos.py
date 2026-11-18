"""Milestones (person_record_history): awards, records, debuts, transfers... one list per person.
FM20 row (44): [00][team u32][u8][person u32][u32][comp u16][award u16][date][A][B][C][D][E u32][type u8][flag u8]
FM24 row (42): [date][A][B][C][D][E u32][type u8][flag u8][00][team u32][person u32][comp u16][award u32][00]
Team, person, competition and award ids are translated; years inside A..E and the date are shifted.
Rows whose award has no FM24 equivalent are dropped."""
import struct, collections
import fm_tad as T
def anio(v, desp): return v + desp if 1990 <= v <= 2100 else v
def convertir(r, desp, t24, p24, c24, a24):
    team, = struct.unpack_from('<I', r, 1); pers, = struct.unpack_from('<I', r, 6)
    comp, award = struct.unpack_from('<HH', r, 14); d, y = struct.unpack_from('<HH', r, 18)
    A = [anio(v, desp) for v in struct.unpack_from('<5I', r, 22)]; tipo, flag = r[42], r[43]
    if award != 0xffff:
        award = a24.get(award)
        if award is None: return None
    else: award = 0xffffffff
    if 1900 < y < 2100:
        y += desp
        if (d & 0x1ff) == 366 and not (y % 4 == 0 and (y % 100 or y % 400 == 0)): d -= 1
    return struct.pack('<HH5IBBBIIHIB', d, y, *A, tipo, flag, 0,
                       t24(team) if team != 0xffffffff else 0xffffffff, p24(pers) if pers != 0xffffffff else 0xffffffff,
                       c24.get(comp, 0xffff) if comp != 0xffff else 0xffff, award, 0)
def transferir(ls20, dt20, ls24, dt24, mapa, desp, t24, p24, c24, a24):
    L20, _, _, a0 = T.leer(ls20); L24, cab, cola, b0 = T.leer(ls24); R20 = T.tam_fila(ls20)
    dt = bytearray(dt24); listas = [list(l) for l in L24]; est = collections.Counter()
    for t, v in mapa:
        if v >= len(L20): continue
        offs = []
        for o in L20[v]:
            r = convertir(dt20[a0 + o:a0 + o + R20], desp, t24, p24, c24, a24)
            if r is None: est['hitos sin premio equivalente'] += 1; continue
            offs.append(len(dt) - b0); dt += r
        while len(listas) <= t: listas.append([])
        listas[t] = offs; est['personas'] += 1; est['hitos'] += len(offs)
    return T.escribir(cab, listas, cola), bytes(dt), est
