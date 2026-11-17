"""historial de competiciones (comp_history): una lista por competicion, una fila por temporada con los clasificados.
fila FM20 (54): [comp u32][año u16][año inicio u16][9 x equipo u32 (1º,2º,3º..., ffffffff)][00][04][año ini u16][año fin u16][fecha u32]
fila FM24 (55): [comp u32][año u16][00 00][9 x equipo u32][00][04][00][año ini u16][año fin u16][fecha u32]
Las competiciones se emparejan por sus campeones historicos (<=2018, por uid de club); los equipos se traducen por uid."""
import struct, collections
import fm_tad as T
Y = lambda r: struct.unpack_from('<H', r, 4)[0]
def equipos(r): return list(struct.unpack_from('<9I', r, 8))
def transferir(ls20, dt20, ls24, dt24, u20, u24, desp, hasta=2018, desde=2020, e20=None, e24=None):
    """u20 / u24: {team id: uid} (fm_uids.mapa); e20 / e24: {stadium id: uid} (fm_estadios.mapa).
    Slots: 0-3 teams (1st, 2nd, 3rd, 4th), 4-6 other data (left empty), 7 final venue (stadium), 8 copied as is."""
    e20 = e20 or {}; e24 = e24 or {}
    s24 = {}
    for k, u in sorted(e24.items()): s24.setdefault(u, k)
    L20, _, _, a0 = T.leer(ls20); L24, cab24, cola24, b0 = T.leer(ls24)
    R20 = T.tam_fila(ls20); R24 = T.tam_fila(ls24)
    t24 = {}
    for t, u in sorted(u24.items()): t24.setdefault(u, t)
    f20 = [[bytes(dt20[a0 + o:a0 + o + R20]) for o in l] for l in L20]
    f24 = [[bytes(dt24[b0 + o:b0 + o + R24]) for o in l] for l in L24]
    # indice FM24: (año, uid campeon) -> listas
    idx = collections.defaultdict(set); comp24 = {}
    for j, rows in enumerate(f24):
        if rows: comp24.setdefault(struct.unpack_from('<I', rows[0], 0)[0], j)
        for r in rows:
            w = equipos(r)[0]
            if Y(r) <= hasta and w in u24: idx[(Y(r), u24[w])].add(j)
    par = {}; est = collections.Counter()
    for i, rows in enumerate(f20):
        if not any(Y(r) >= desde for r in rows): continue
        ks = [(Y(r), u20.get(equipos(r)[0])) for r in rows if Y(r) <= hasta]
        v = collections.Counter(j for k in ks for j in idx.get(k, ()))
        top = v.most_common(2) + [(None, 0), (None, 0)]
        if top[0][1] >= max(2, 0.5 * len(ks)) and top[0][1] > top[1][1]: par[i] = top[0][0]; est['comp por campeones'] += 1
        else: est['comp sin pareja'] += 1
    dt = bytearray(dt24); extra = bytearray(); listas = [list(l) for l in L24]; base = len(dt) - b0
    def fila_de(o): return bytes(dt[b0 + o:b0 + o + R24]) if o < base else bytes(extra[o - base:o - base + R24])
    for i, j in par.items():
        sitio = {Y(r): o for r, o in zip(f24[j], L24[j])}
        plantilla = f24[j][-1] if f24[j] else None
        for r in f20[i]:
            if Y(r) < desde: continue
            yt = Y(r) + desp; eq = []
            for k, t in enumerate(equipos(r)):
                if t == 0xffffffff or 4 <= k <= 6: eq.append(0xffffffff); continue
                if k == 8: eq.append(t); continue
                if k == 7:
                    n = s24.get(e20.get(t))
                    if n is None: est['estadio sin equivalente'] += 1
                    eq.append(0xffffffff if n is None else n); continue
                n = t24.get(u20.get(t))
                if n is None: est['equipo sin equivalente'] += 1
                eq.append(0xffffffff if n is None else n)
            if eq[0] == 0xffffffff: est['temporada sin campeon equivalente'] += 1; continue
            o = sitio.get(yt)
            nueva = bytearray(fila_de(o) if o is not None else plantilla)
            struct.pack_into('<H', nueva, 4, yt); struct.pack_into('<9I', nueva, 8, *eq)
            a, b = struct.unpack_from('<HH', r, R20 - 8)
            struct.pack_into('<HH', nueva, R24 - 8, a + desp, b + desp)
            d, fy = struct.unpack_from('<HH', r, R20 - 4)
            struct.pack_into('<HH', nueva, R24 - 4, d, fy + desp if fy != 0x76c else fy)
            if o is not None: dt[b0 + o:b0 + o + R24] = nueva; est['temporadas sobrescritas'] += 1
            else:
                o = base + len(extra); extra += nueva; l = listas[j]; k = 0
                while k < len(l) and Y(fila_de(l[k])) <= yt: k += 1
                l.insert(k, o); est['temporadas añadidas'] += 1
    nls = T.escribir(cab24, listas, cola24) if extra else ls24
    return nls, bytes(dt + extra), est, par

# --- latest seasons stored inside game_db.dat (the database keeps the rows of the last finished season(s);
#     comp_history only receives them when the next season starts) ---
import re
def filas_db(m, ver, anios):
    """{(comp, year): (position, row bytes)} for the comp-history rows embedded in game_db.
    FM20 (54 bytes): [comp][year][start year][9 x u32][00 04][start][end][date]
    FM24 (55 bytes): [comp][year][00 00][9 x u32][00 04 00][start][end][date]   (one pass over the file)"""
    anios = set(anios); out = {}; R = 54 if ver == 20 else 55
    pat = re.compile(rb'(?=(.{4})(.{2})' + (rb'.{2}.{36}\x00\x04.{2}' if ver == 20 else rb'\x00\x00.{36}\x00\x04\x00.{2}') + rb'\2)', re.S)
    for x in pat.finditer(m):
        y = struct.unpack('<H', x.group(2))[0]
        if y in anios: out.setdefault((struct.unpack('<I', x.group(1))[0], y), (x.start(), bytes(m[x.start():x.start() + R])))
    return out
def transferir_db(m24, m20, ls20, dt20, ls24, dt24, par, u20, u24, e20, e24, desp, desde=2020):
    """Overwrites, in place inside the FM24 game_db (bytearray m24), the embedded rows of the seasons
    that also exist in FM20 (comp_history rows or FM20 embedded rows)."""
    L20, _, _, a0 = T.leer(ls20); L24, _, _, b0 = T.leer(ls24)
    R20 = T.tam_fila(ls20)
    c2c = {}
    for i, j in par.items():
        if L20[i] and L24[j]: c2c[struct.unpack_from('<I', dt20, a0 + L20[i][0])[0]] = struct.unpack_from('<I', dt24, b0 + L24[j][0])[0]
    fuente = {}
    for l in L20:
        for o in l:
            r = bytes(dt20[a0 + o:a0 + o + R20]); y = Y(r)
            if y >= desde: fuente[(struct.unpack_from('<I', r, 0)[0], y)] = r
    fin20 = max(y for _, y in fuente) if fuente else 2030
    for k, (p, r) in filas_db(m20, 20, range(desde, fin20 + 2)).items(): fuente[k] = r
    destino = filas_db(m24, 24, sorted({y + desp for _, y in fuente}))
    t24 = {}
    for t, u in sorted(u24.items()): t24.setdefault(u, t)
    s24 = {}
    for k, u in sorted(e24.items()): s24.setdefault(u, k)
    est = collections.Counter()
    for (c20, y), r in fuente.items():
        c24 = c2c.get(c20)
        if c24 is None or (c24, y + desp) not in destino: continue
        p, viejo = destino[(c24, y + desp)]; nueva = bytearray(viejo)
        eq = []
        for k, t in enumerate(equipos(r)):
            if t == 0xffffffff or 4 <= k <= 6: eq.append(0xffffffff)
            elif k == 8: eq.append(t)
            elif k == 7: eq.append(s24.get(e20.get(t), 0xffffffff))
            else: eq.append(t24.get(u20.get(t), 0xffffffff))
        if eq[0] == 0xffffffff: est['bd: temporada sin campeon equivalente'] += 1; continue
        struct.pack_into('<9I', nueva, 8, *eq)
        a, b = struct.unpack_from('<HH', r, 46); struct.pack_into('<HH', nueva, 47, a + desp, b + desp)
        d, fy = struct.unpack_from('<HH', r, 50); struct.pack_into('<HH', nueva, 51, d, fy + desp if fy != 0x76c else fy)
        m24[p:p + 55] = nueva; est['bd: temporadas sobrescritas'] += 1
    return est
