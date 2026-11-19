"""Teams of every club: the club record lists them as [n u8][n team ids], the first being the first team (the team
whose record has the club's unique id). FM20 Espanyol: 1497 first team, 71623 under-19, 127051; FM24 2031:
1439, 47833 (under-19). Youth teams have their own unique id, different in FM20 and FM24, so they are matched by
club and by their place in this list."""
import struct
import fm_clubnames as N
def equipos_por_club(m, tz):
    """{club uid: [team ids]}; tz = fm_ligas.team_zone(m) (first teams)"""
    primero = {}
    for t, v in tz.items(): primero.setdefault(v['uid'], t)
    cabs = N.cabeceras(m); out = {}
    for i, (p, u, _) in enumerate(cabs):
        t = primero.get(u)
        if t is None: continue
        fin = cabs[i + 1][0] if i + 1 < len(cabs) else p + 200000
        k = struct.pack('<I', t); q = m.find(k, p + 12, fin)
        while q >= 0:
            n = m[q - 1]
            if 1 <= n <= 8:
                ids = list(struct.unpack_from('<%dI' % n, m, q))
                if all(0 < x < 400000 for x in ids) and len(set(ids)) == n: out[u] = ids; break
            q = m.find(k, q + 1, fin)
    return out
def mapa_secundarios(m20, m24, t20, t24, tr):
    """{FM20 team: FM24 team} for the second, third... teams of each club (same place in the club's list)"""
    c20 = equipos_por_club(m20, t20); c24 = equipos_por_club(m24, t24); out = {}
    for u, ids in c20.items():
        u2 = tr.get(u, u)
        if u2 is None or u2 not in c24: continue
        for k, t in enumerate(ids[1:], 1):
            if k < len(c24[u2]): out[t] = c24[u2][k]
    return out
