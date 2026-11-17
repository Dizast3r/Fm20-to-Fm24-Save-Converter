"""localiza los campos del contrato caminando hacia atras desde el id de persona (k).
Estructura (de atras hacia delante):  ... ff*n 00 00 [N primas][N x 8 bytes][N2][N2 x E2 bytes][cola fija] ff*8 FIN ALTA [5 bytes][n u32][lista n x E][relleno] INICIO [4 bytes, el ultimo = dorsal] ... [id persona][club][sueldo]"""
import struct
C = {7: dict(start=23, tail=1, fixed=20, e2=tuple(range(24, 37)), esz=(29,)),
     8: dict(start=24, tail=2, fixed=22, e2=(31,), esz=tuple(range(20, 61)))}
def okdate(m, p, lo=1899, hi=2060):
    d, y = struct.unpack_from('<HH', m, p); return lo <= y <= hi and 1 <= (d & 0x1ff) <= 366
def _end(m, st, c):
    e = st - c['tail'] - 17           # caso habitual: lista intermedia vacia
    if e > 8 and m[e - 8:e] == b'\xff' * 8 and okdate(m, e): return e
    # contrato de un jugador cedido: los 8 bytes previos no son ff (datos de la cesion), las dos fechas si son validas
    if e > 8 and okdate(m, e) and okdate(m, e + 4) and m[e - 8:e - 4] == b'\xff' * 4: return e
    q = st
    for _ in range(80):
        q = m.rfind(b'\xff' * 8, max(0, st - 6000), q)
        if q < 0: return None
        e = q + 8
        if e + 17 <= st - c['tail'] and okdate(m, e):
            n = struct.unpack_from('<I', m, e + 13)[0]; ln = st - c['tail'] - (e + 17)
            if 0 < n < 200 and ln % n == 0 and ln // n in c['esz']: return e
    return None
def fields(m, k, ver):
    c = C[ver]; st = k - c['start']
    if st < 100 or not okdate(m, st): return None
    e = _end(m, st, c)
    if e is None: return None
    X = e - 8 - c['fixed']            # fin de la segunda lista
    for n2 in range(0, 25):
        for e2 in (c['e2'] if n2 else c['e2'][:1]):
            c2 = X - e2 * n2 - 1
            if c2 < 16 or m[c2] != n2: continue
            for n in range(15, -1, -1):
                cp = c2 - 8 * n - 1
                if m[cp] != n or m[cp - 2:cp] != b'\0\0' or 0xff not in (m[cp - 3], m[cp - 4]): continue
                ok = True
                for i in range(n):
                    par, typ = struct.unpack_from('<HH', m, cp + 1 + 8 * i + 4)
                    if typ >= 0x80 or not (par == 0xffff or par < 2000): ok = False; break
                if ok: return dict(start=st, end=e, date2=e + 4, count=cp, n=n, n2=n2, squad=st + 4, wage_k=k)
    return None
