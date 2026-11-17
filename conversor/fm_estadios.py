"""stadiums: id -> uid. Record in game_db: [stadium-1][uid][uid] 00 [capacity u32]...; the records are stored
consecutively with increasing ids. Stadium ids differ between FM20 and FM24, uids are stable."""
import re, struct
ANCLA = re.compile(rb'(?=(.{4})(.{4})\2\x00(.{4})\3\3)', re.S)
PAT = re.compile(rb'(?=(.{4})(.{4})\2\x00)', re.S)
def mapa(m):
    pos = []
    for x in ANCLA.finditer(m, 0, min(len(m), 160 << 20)):
        s = struct.unpack('<I', x.group(1))[0] + 1; u = struct.unpack('<I', x.group(2))[0]
        if s < 200000 and 0 < u < 0xffffffff and struct.unpack('<I', x.group(3))[0] < 200000: pos.append((x.start(), s))
    # zona de la tabla: el tramo mas largo de anclas con ids crecientes
    pos.sort(); best = []; cur = []
    for p, s in pos:
        if cur and (s <= cur[-1][1] or p - cur[-1][0] > 400000): best = max(best, cur, key=len); cur = []
        cur.append((p, s))
    best = max(best, cur, key=len)
    lo, hi = best[0][0] - 200000, best[-1][0] + 200000
    cand = []
    for x in PAT.finditer(m, max(0, lo), min(len(m), hi)):
        s = struct.unpack('<I', x.group(1))[0] + 1; u = struct.unpack('<I', x.group(2))[0]
        if s < 200000 and 0 < u < 0xffffffff and u != s - 1: cand.append((x.start(), s, u))
    # quedarse con la secuencia creciente de ids mas larga (LIS por posicion)
    import bisect
    tails = []; idx = []; prev = [None] * len(cand)
    for k, (p, s, u) in enumerate(cand):
        q = bisect.bisect_left(tails, s)
        if q == len(tails): tails.append(s); idx.append(k)
        else: tails[q] = s; idx[q] = k
        prev[k] = idx[q - 1] if q else None
    k = idx[-1] if idx else None; out = {}
    while k is not None: out[cand[k][1]] = cand[k][2]; k = prev[k]
    return out
