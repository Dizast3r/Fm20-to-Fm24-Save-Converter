"""lista de plantilla de cada equipo: va poco despues de su ficha [id-1][uid][uid] 0a 00 ...  como [ff ff ff ff][n u16][n x id persona]"""
import struct
def squad_of(m, v, maxid=3000000):
    p = v['pos']
    for q in range(p + 20, p + 400):
        if m[q:q + 4] != b'\xff\xff\xff\xff': continue
        n = struct.unpack_from('<H', m, q + 4)[0]
        if not 0 < n <= 300: continue
        ids = struct.unpack_from('<%dI' % n, m, q + 6)
        if len(set(ids)) == n and all(0 < i < maxid for i in ids): return q + 4, n, ids
    return None
