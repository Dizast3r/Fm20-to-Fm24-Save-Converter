"""indice de club (campo 'a', el que usan premios y otros historiales como a+1) -> uid del club"""
import re, struct
PAT = {7: re.compile(rb'(.{4})(.{4})\2\x00.{4}(.{4}).{4}\3', re.S),
       8: re.compile(rb'(.{4})(.{4})\2\x00(.{4})\xff\xff\xff\xff\3\3', re.S)}
def mapa(m, ver):
    out = {}
    for x in PAT[ver].finditer(m):
        a = struct.unpack('<I', x.group(1))[0]; u = struct.unpack('<I', x.group(2))[0]
        if a < 300000 and 0 < u < 90000000: out.setdefault(a, u)
    return out
