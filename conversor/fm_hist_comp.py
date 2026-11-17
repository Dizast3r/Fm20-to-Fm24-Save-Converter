"""historial de competiciones (comp_history): una lista por competicion, una fila por temporada con los clasificados.
fila FM20 (54): [comp u32][año u16][año inicio u16][9 x equipo u32 (1º,2º,3º..., ffffffff)][00][04][año ini u16][año fin u16][fecha u32]
fila FM24 (55): [comp u32][año u16][00 00][9 x equipo u32][00][04][00][año ini u16][año fin u16][fecha u32]
Las competiciones se emparejan por sus campeones historicos (<=2018, por uid de club); los equipos se traducen por uid."""
import struct, collections
import fm_tad as T
Y = lambda r: struct.unpack_from('<H', r, 4)[0]
def equipos(r): return list(struct.unpack_from('<9I', r, 8))
def transferir(ls20, dt20, ls24, dt24, u20, u24, desp, hasta=2018, desde=2020):
    """u20 / u24: {id de equipo: uid} (fm_uids.mapa)"""
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
            for t in equipos(r):
                if t == 0xffffffff: eq.append(t); continue
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
