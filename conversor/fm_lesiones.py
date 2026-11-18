"""Injury history (injury_histories, 18-byte rows): the list index of every person is stored in his record, between
the attribute block and the name record, as [ffffffff][date][date][00 00][list u32][03 00 00 00]."""
import re, struct, bisect
PAT = re.compile(rb'\xff\xff\xff\xff(..[\xc0-\xff]\x07)(..[\xc0-\xff]\x07)\x00\x00(.{4})\x03\x00\x00\x00', re.S)
def indices(m, jugadores):
    """jugadores: {pid: (pos_bloque, pos_nombre)} -> {pid: (position of the field, list)}"""
    orden = sorted((pb, pn, p) for p, (pb, pn) in jugadores.items())
    starts = [x[0] for x in orden]; out = {}
    for x in PAT.finditer(m, starts[0] if starts else 0):
        q = x.start(3); i = bisect.bisect_right(starts, q) - 1
        if i < 0: continue
        pb, pn, p = orden[i]
        if pb <= q < pn and p not in out: out[p] = (q, struct.unpack('<I', x.group(3))[0])
    return out

def campo(m, pb, pn):
    """(position, list) of the injury field of the player whose record goes from pb to pn"""
    x = PAT.search(m, pb, pn)
    return (x.start(3), struct.unpack('<I', x.group(3))[0]) if x else None
def convertir(r20, desp):
    """FM20 18 bytes [type u32][u32][u8][u8 b][date][days u16][2 bytes] -> FM24 16 bytes [type u16][ffffffff][00][b][date][days u32]"""
    t = struct.unpack_from('<I', r20, 0)[0]; b = r20[9]; d, y = struct.unpack_from('<HH', r20, 10); dias = struct.unpack_from('<H', r20, 14)[0]
    if 1900 < y < 2100:
        y += desp
        if (d & 0x1ff) == 366 and not (y % 4 == 0 and (y % 100 or y % 400 == 0)): d -= 1
    return struct.pack('<HIBBHHI', t, 0xffffffff, 0, b, d, y, dias)
def transferir(ls20, dt20, ls24, dt24, mapa, desp):
    import fm_tad as T, collections
    L20, _, _, a0 = T.leer(ls20); L24, cab, cola, b0 = T.leer(ls24); R20 = T.tam_fila(ls20)
    dt = bytearray(dt24); listas = [list(l) for l in L24]; est = collections.Counter()
    for t, v in mapa:
        if v >= len(L20): continue
        offs = []
        filas = sorted((convertir(dt20[a0 + o:a0 + o + R20], desp) for o in L20[v]), key=lambda r: struct.unpack_from('<HH', r, 8)[::-1])
        for r in filas: offs.append(len(dt) - b0); dt += r
        while len(listas) <= t: listas.append([])
        listas[t] = offs; est['jugadores'] += 1; est['lesiones'] += len(offs)
    return T.escribir(cab, listas, cola), bytes(dt), est
