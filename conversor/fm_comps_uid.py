"""Competition id -> unique id (uid). Records [comp-1][uid][uid] 00 [u8][u8] 01 ... followed by a run of 06 bytes
(the competition record); ids referenced elsewhere (milestones, comp_history) are record id + 1."""
import re, struct
PAT = re.compile(rb'(?=(.{4})(.{4})\2\x00[\x00-\x04][\x00-\x04]\x01.{8,60}?\x06\x06\x06\x06\x06\x06)', re.S)
def mapa(m):
    out = {}
    for x in PAT.finditer(m, 0, min(len(m), 64 << 20)):
        t = struct.unpack('<I', x.group(1))[0] + 1; u = struct.unpack('<I', x.group(2))[0]
        if t > 20000 or not 0 < u < 0xffffffff or u == t - 1: continue
        out.setdefault(t, u)
    return out
def pares(m20, m24):
    a, b = mapa(m20), mapa(m24); ib = {}
    for t, u in sorted(b.items()): ib.setdefault(u, t)
    return {t: ib[u] for t, u in a.items() if u in ib}
