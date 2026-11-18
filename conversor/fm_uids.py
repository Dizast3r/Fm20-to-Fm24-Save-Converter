"""Team id -> unique id (uid). Records [team-1][uid][uid] + type byte:
 - clubs, reserve and youth teams: type 0x0a (+ flag), around Espanyol's record (uid 1724)
 - national teams: type 0x0b followed by a date [u16][year u16], in the same area
(Records [id][uid][uid] 00 01 01 01 01 near the start of game_db are cities, not national teams:
 their ids overlap the team ids, so they must not be used.)"""
import re, struct
PAT = re.compile(rb'(?=(.{4})(.{4})\2\x0a)', re.S)
NAT = re.compile(rb'(?=(.{4})(.{4})\2\x0b..(..))', re.S)
def mapa(m, rango=60 << 20):
    z = m.find(struct.pack('<II', 1724, 1724) + b'\x0a\x00'); out = {}
    lo, hi = max(0, z - rango), min(len(m), z + rango)
    for x in NAT.finditer(m, lo, hi):
        t = struct.unpack('<I', x.group(1))[0] + 1; u = struct.unpack('<I', x.group(2))[0]
        if t > 400000 or not 0 < u < 0xffffffff or u == t - 1 or not 1900 <= struct.unpack('<H', x.group(3))[0] < 2100: continue
        out.setdefault(t, u)
    for x in PAT.finditer(m, lo, hi):
        t = struct.unpack('<I', x.group(1))[0] + 1; u = struct.unpack('<I', x.group(2))[0]
        if t > 400000 or not 0 < u < 0xffffffff or u == t - 1: continue
        out.setdefault(t, u)
    return out
