"""Team id -> unique id (uid). Records [team-1][uid][uid] + type byte:
 - clubs, reserve and youth teams: type 0x0a (+ flag), around Espanyol's record (uid 1724)
 - national teams: type 0x0b followed by a date [u16][year u16], in the same area (only for ids that are not clubs)
(Records [id][uid][uid] 00 01 01 01 01 near the start of game_db are cities, not national teams:
 their ids overlap the team ids, so they must not be used.)"""
import re, struct
PAT = re.compile(rb'(?=(.{4})(.{4})\2\x0a)', re.S)
NAT = re.compile(rb'(?=(.{4})(.{4})\2\x0b..(..))', re.S)
def mapa(m, rango=60 << 20):
    z = m.find(struct.pack('<II', 1724, 1724) + b'\x0a\x00'); out = {}
    lo, hi = max(0, z - rango), min(len(m), z + rango)
    dist = {}   # several matches for one id: the team records are stored together, keep the one closest to Espanyol's
    for x in PAT.finditer(m, lo, hi):
        t = struct.unpack('<I', x.group(1))[0] + 1; u = struct.unpack('<I', x.group(2))[0]
        if t > 400000 or not 0 < u < 0xffffffff or u == t - 1: continue
        d = abs(x.start() - z)
        if t not in dist or d < dist[t]: dist[t] = d; out[t] = u
    for x in NAT.finditer(m, lo, hi):
        t = struct.unpack('<I', x.group(1))[0] + 1; u = struct.unpack('<I', x.group(2))[0]
        if t > 400000 or not 0 < u < 0xffffffff or u == t - 1 or not 1900 <= struct.unpack('<H', x.group(3))[0] < 2100: continue
        out.setdefault(t, u)
    return out

def traduccion(m20, m24):
    """FM20 club uid -> FM24 club uid (see fm_clubnames.traduccion): some clubs got another uid in FM24 and their old
    uid may belong to another club there. Returns {uid20: uid24 or None (no equivalent)} only for the uids that change."""
    import fm_clubnames as N
    n20 = N.nombres(m20); n24 = N.nombres(m24)
    tr, est = N.traduccion(n20, n24)
    out = {u: v for u, v in tr.items() if v != u and (v is not None or u in n24)}
    return out, est
def aplicar(tr, uid):
    """uid of an FM20 team in FM24 terms; a uid that FM24 gives to another club becomes unique and unmatched"""
    if uid not in tr: return uid
    v = tr[uid]
    return v if v is not None else 0x80000000 | uid
def traducir_zona(ts, tr):
    """team_zone() of FM20, in place"""
    for v in ts.values(): v['uid'] = aplicar(tr, v['uid'])
    return ts
