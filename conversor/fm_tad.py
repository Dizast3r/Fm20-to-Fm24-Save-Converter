"""ficheros 'tad' (_ls.dat): listas de offsets dentro del _dt.cmt correspondiente.
v3 (FM20): 02 01 'tad.' 03 00 00 | libres u32 (en 9) | libres x u32 | n u32 | n x [c][c x u32 offset] | cola
v4 (FM24): 03 01 'tad.' 04 00    | libres u32 (en 8) | libres x u32 | n u32 | n x [c][c x u32 codificado] | cola
   codificacion v4: S0 = T0, Sk = Tk - S(k-1)  (decodificar: Tk = Sk + S(k-1)).
'libres' = huecos de filas reutilizables del _dt. cola = [u32 0][u32 tamaño de fila][u16 version del _dt]
Cabecera de _dt.cmt: v3 9 bytes, v4 8 bytes."""
import struct
def _pf(ls): return 9 if ls[0] == 2 else 8
def cab(ls):
    pf = _pf(ls); f = struct.unpack_from('<I', ls, pf)[0]
    return pf + 4 + 4 * f, (9 if ls[0] == 2 else 8)
def leer(ls):
    pn, d0 = cab(ls); v4 = ls[0] != 2
    n = struct.unpack_from('<I', ls, pn)[0]; p = pn + 4; out = []
    for _ in range(n):
        c = struct.unpack_from('<I', ls, p)[0]; o = list(struct.unpack_from('<%dI' % c, ls, p + 4)); p += 4 + 4 * c
        if v4:
            for k in range(c - 1, 0, -1): o[k] = (o[k] + o[k - 1]) & 0xffffffff
        out.append(o)
    return out, ls[:pn], ls[p:], d0
def libres(ls):
    pf = _pf(ls); f = struct.unpack_from('<I', ls, pf)[0]
    return list(struct.unpack_from('<%dI' % f, ls, pf + 4))
def tam_fila(ls): return struct.unpack_from('<I', ls, len(ls) - 6)[0]
def escribir(cabecera, listas, cola):
    v4 = cabecera[0] != 2
    b = bytearray(cabecera) + struct.pack('<I', len(listas))
    for o in listas:
        s = list(o)
        if v4:
            for k in range(1, len(s)): s[k] = (o[k] - s[k - 1]) & 0xffffffff
        b += struct.pack('<I', len(s)) + struct.pack('<%dI' % len(s), *s)
    return bytes(b + cola)
