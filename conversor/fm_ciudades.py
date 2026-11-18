"""Cities: records [city-1][uid][uid] 00 [latitude f32][longitude f32][u8][nation u32]... at the start of game_db.
People reference a city as id + 1 (birthplace: name record, birth date + 25 in FM24 / + 21 in FM20).
FM20 -> FM24: same uid when the coordinates agree, otherwise the closest FM24 city of the same nation."""
import re, struct, math, collections
PAT = re.compile(rb'(?=(.{4})(.{4})\2\x00\x00(.{4})(.{4})(.)(.{4}))', re.S)
def ciudades(m, hi=8 << 20):
    out = {}
    for x in PAT.finditer(m, 0, min(len(m), hi)):
        i, u = struct.unpack('<II', x.group(1) + x.group(2))
        la, lo = struct.unpack('<ff', x.group(3) + x.group(4)); n = struct.unpack('<I', x.group(6))[0]
        if i < 500000 and 0 < u < 0x7fffffff and -90 <= la <= 90 and -180 <= lo <= 180 and (la or lo) and n < 300:
            out.setdefault(i + 1, (u, la, lo, n))
    return out
def traduccion(c20, c24):
    """{FM20 city id: FM24 city id}"""
    porid = {}; pornac = collections.defaultdict(list)
    for i, (u, la, lo, n) in c24.items(): porid.setdefault(u, i); pornac[n].append((la, lo, i))
    out = {}; est = collections.Counter()
    for i, (u, la, lo, n) in c20.items():
        j = porid.get(u)
        if j is not None and abs(c24[j][1] - la) < 0.2 and abs(c24[j][2] - lo) < 0.2: out[i] = j; est['mismo uid'] += 1; continue
        cand = pornac.get(n)
        if not cand: est['sin equivalente'] += 1; continue
        d, k = min(((la - a) ** 2 + ((lo - b) * math.cos(math.radians(la))) ** 2, k) for a, b, k in cand)
        if d < 0.05 ** 2: out[i] = k; est['por coordenadas'] += 1
        else: est['sin equivalente'] += 1
    return out, est
