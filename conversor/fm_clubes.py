"""tabla de clubes: campo 'a' (+ desfase = id_club de las fichas de jugador), id unico de base de datos y nombres"""
import re, struct
PAT = {8: re.compile(rb'(.{4})(.{4})\2\x00(.{4})\xff\xff\xff\xff\3\3.{4}.{0,12}?\x01\x01', re.S),
       7: re.compile(rb'(.{4})(.{4})\2\x00.{4}(.{4}).{4}\3.{40,200}?\xff\xff\xff\xff\x00\x01\x01[\x00-\x03]', re.S)}
def clubs(m, ver, limit=None):
    out = []; seen = set()
    for x in PAT[ver].finditer(m, 0, limit or len(m)):
        p = x.end(); n = struct.unpack_from('<I', m, p)[0]
        if not 0 < n < 120: continue
        try: long = m[p + 4:p + 4 + n].decode('utf8')
        except UnicodeDecodeError: continue
        q = p + 4 + n; n2 = struct.unpack_from('<I', m, q)[0]
        if not 0 < n2 < 80: continue
        try: short = m[q + 4:q + 4 + n2].decode('utf8')
        except UnicodeDecodeError: continue
        a = struct.unpack_from('<I', x.group(1))[0]; uid = struct.unpack_from('<I', x.group(2))[0]
        if a > 300000 or uid in seen: continue
        seen.add(uid)
        out.append(dict(pos=x.start(), a=a, uid=uid, nation=struct.unpack_from('<I', x.group(3))[0], long=long, short=short, after=q + 4 + n2))
    return out
