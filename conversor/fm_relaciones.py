"""Club relationships (legends, icons, favoured personnel, rivals...): the list at the end of every club record,
[u8 count][entries] followed by 00 00.
FM20 entry 12 bytes [id u32][kind u8][00][cat u8][sub u8][level u8][flag u8][u8][ff]
FM24 entry 16 bytes [id u32][00 00 00 00][kind u8][00][cat u8][sub u8][level u8][flag u8][u8][ff]
cat 3 / sub 1: a person (id = pid + 1; kind = role: 1 player, 2 staff, 5 player and manager...). Legends and icons
carry flag 0x4f (legends with the highest level), the favoured personnel are the other high levels.
Other entries (cat 1, cat 3 / sub 2...) point to clubs and other things and are left as they are in FM24."""
import struct
import fm_clubnames as N
def _lista(m, fin, ver):
    R = 12 if ver == 7 else 16
    p = fin; n = 0; mejor = None
    while p - R > 0:
        e = m[p - R:p]
        if e[-1] != 0xff or e[R - 7] != 0 or (ver == 8 and e[4:8] != b'\x00\x00\x00\x00'): break
        p -= R; n += 1
        if m[p - 1] == n % 256: mejor = (p - 1, n)
    return mejor
def listas(m, ver):
    """{club uid: (count position, n, [entries])}"""
    R = 12 if ver == 7 else 16
    cabs = N.cabeceras(m); out = {}
    for i, (p, u, _) in enumerate(cabs[:-1]):
        fin = cabs[i + 1][0]
        if m[fin - 2:fin] != b'\x00\x00': continue
        r = _lista(m, fin - 2, ver)
        if r: out.setdefault(u, (r[0], r[1], [bytes(m[r[0] + 1 + R * k:r[0] + 1 + R * (k + 1)]) for k in range(r[1])]))
    return out
def persona(e, ver):
    """(pid + 1) if the entry is a person relationship, else None"""
    k = 4 if ver == 7 else 8
    return struct.unpack_from('<I', e, 0)[0] if e[k + 2] == 3 and e[k + 3] == 1 else None
def a_fm24(e, pid24):
    return struct.pack('<II', pid24, 0) + e[4:]
