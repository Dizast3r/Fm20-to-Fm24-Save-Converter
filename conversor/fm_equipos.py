"""fichas de equipo: id de equipo (el id_club de los jugadores), id unico, division actual y anterior, lista de plantilla"""
import re, struct
PAT = re.compile(rb'(.{4})(.{4})\2\x0a\x00.{3}(.{4})(.{4})', re.S)
def teams(m, lo, hi):
    out = {}
    for x in PAT.finditer(m, lo, hi):
        t = struct.unpack('<I', x.group(1))[0] + 1; uid = struct.unpack('<I', x.group(2))[0]
        div = struct.unpack('<I', x.group(3))[0]; last = struct.unpack('<I', x.group(4))[0]
        if t > 400000 or uid > 90000000: continue
        out.setdefault(t, dict(pos=x.start(), uid=uid, div=div, last=last, divpos=x.start() + 17))
    return out
