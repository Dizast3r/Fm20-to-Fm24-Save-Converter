"""id de equipo -> id unico (uid). Fichas [equipo-1][uid][uid] + tipo:
 - clubes, filiales, juveniles: tipo 0x0a (+ indicador) alrededor de la ficha del Espanyol (uid 1724)
 - selecciones: 00 01 01 01 01 al principio de game_db"""
import re, struct
PAT = re.compile(rb'(?=(.{4})(.{4})\2\x0a)', re.S)
NAT = re.compile(rb'(?=(.{4})(.{4})\2\x00\x01\x01\x01\x01)', re.S)
def mapa(m, rango=60 << 20):
    z = m.find(struct.pack('<II', 1724, 1724) + b'\x0a\x00'); out = {}
    for pat, lo, hi in ((PAT, max(0, z - rango), min(len(m), z + rango)), (NAT, 0, min(len(m), 40 << 20))):
        for x in pat.finditer(m, lo, hi):
            t = struct.unpack('<I', x.group(1))[0] + 1; u = struct.unpack('<I', x.group(2))[0]
            if t > 400000 or not 0 < u < 0xffffffff or u == t - 1: continue
            out.setdefault(t, u)
    return out
