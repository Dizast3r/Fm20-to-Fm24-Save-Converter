"""premios por temporada (award_year_hist): una lista por premio, una fila por año con 3 clasificados.
fila (82): [año u16][premio u16] + 3 x [persona u32][equipo u32][edad u8][4 (FM24: 0)][u16][u32][u16][u16][u8][nacion u16]
Premios FM20<->FM24 emparejados por los ganadores historicos (<=2018, por uid de jugador). Personas: pareja del trasplante
(jugador FM20 -> ficha FM24 que lo recibe) o mismo uid; equipos por uid de club."""
import struct, collections
import fm_tad as T
VACIA = bytes.fromhex('ffffffffffffffff' + '00' * 11 + '02' + '00' * 4 + 'ffff')
Y = lambda r: struct.unpack_from('<H', r, 0)[0]
def leer_pares(path):
    m = {}
    for tok in open(path).read().split():
        x = tok.split(':')
        if len(x) >= 2 and x[0].isdigit() and x[1].isdigit(): m[int(x[0])] = int(x[1])
    return m
def transferir(ls20, dt20, ls24, dt24, pu20, pu24, pares, tu20, tu24, campo24, desp, hasta=2018, desde=2020):
    """pu20/pu24: {id de persona (pid, el de la ficha): uid}; en las filas la persona va como pid+1.
    tu20/tu24: {equipo: uid}; en las filas el club va como uid+1 (igual en FM24). campo24: {uid de club: valor del campo en FM24}"""
    L20, _, _, a0 = T.leer(ls20); L24, cab24, cola24, b0 = T.leer(ls24); R = 82
    f20 = [[bytes(dt20[a0 + o:a0 + o + R]) for o in l] for l in L20]
    f24 = [[bytes(dt24[b0 + o:b0 + o + R]) for o in l] for l in L24]
    p_por_uid = {}
    for p, u in pu24.items(): p_por_uid.setdefault(u, p)
    AW = lambda rows: struct.unpack_from('<H', rows[0], 2)[0] if rows else None
    gan24 = []
    por_id = collections.defaultdict(list)
    for j, rows in enumerate(f24):
        gan24.append({(Y(r), pu24.get(struct.unpack_from('<I', r, 4)[0] - 1)) for r in rows if Y(r) <= hasta})
        if rows: por_id[AW(rows)].append(j)
    par = {}; est = collections.Counter(); usados = set()
    for i, rows in enumerate(f20):
        if not any(Y(r) >= desde for r in rows): continue
        ks = {(Y(r), pu20.get(struct.unpack_from('<I', r, 4)[0] - 1)) for r in rows if Y(r) <= hasta}
        ks = {k for k in ks if k[1] is not None}
        a = AW(rows); best = (0, None)
        for d in range(-12, 13):
            for j in por_id.get(a + d, ()):
                sc = len(ks & gan24[j])
                if sc > best[0]: best = (sc, j)
        if best[1] is not None and best[0] >= 2 and best[0] >= 0.4 * len(ks) and best[1] not in usados:
            par[i] = best[1]; usados.add(best[1]); est['premios emparejados'] += 1
        else: est['premios sin pareja'] += 1
    def persona(p):
        p -= 1
        if p in pares: return pares[p] + 1
        u = pu20.get(p)
        q = p_por_uid.get(u) if u is not None else None
        return None if q is None else q + 1
    dt = bytearray(dt24); extra = bytearray(); listas = [list(l) for l in L24]; base = len(dt) - b0
    def fila_de(o): return bytes(dt[b0 + o:b0 + o + R]) if o < base else bytes(extra[o - base:o - base + R])
    for i, j in par.items():
        sitio = {Y(r): o for r, o in zip(f24[j], L24[j])}
        cab = f24[j][-1][:4] if f24[j] else None
        for r in f20[i]:
            if Y(r) < desde: continue
            nueva = bytearray(cab + bytes(R - 4)); struct.pack_into('<H', nueva, 0, Y(r) + desp)
            for e in range(3):
                x = bytearray(r[4 + 26 * e:30 + 26 * e]); p, t = struct.unpack_from('<II', x, 0)
                if p == 0xffffffff: nueva[4 + 26 * e:30 + 26 * e] = VACIA; continue
                p2 = persona(p); t2 = 0xffffffff if t == 0xffffffff else campo24.get(t - 1, 0xffffffff)
                if p2 is None: est['persona sin equivalente'] += 1; nueva[4 + 26 * e:30 + 26 * e] = VACIA; continue
                struct.pack_into('<II', x, 0, p2, t2); x[9:13] = b'\0\0\0\0'
                nueva[4 + 26 * e:30 + 26 * e] = x
            if struct.unpack_from('<I', nueva, 4)[0] == 0xffffffff: est['año sin ganador equivalente'] += 1; continue
            yt = Y(r) + desp; o = sitio.get(yt)
            if o is not None: dt[b0 + o:b0 + o + R] = nueva; est['años sobrescritos'] += 1
            else:
                o = base + len(extra); extra += nueva; l = listas[j]; k = 0
                while k < len(l) and Y(fila_de(l[k])) <= yt: k += 1
                l.insert(k, o); est['años añadidos'] += 1
    nls = T.escribir(cab24, listas, cola24) if extra else ls24
    return nls, bytes(dt + extra), est, par

def campo_club24(ls24, dt24, club24, tu24, desde=2021):
    """uid de club -> valor del campo club en los premios de FM24 (votado con el club actual de los premiados)"""
    L, _, _, b0 = T.leer(ls24); v = collections.defaultdict(collections.Counter)
    for l in L:
        for o in l:
            r = dt24[b0 + o:b0 + o + 82]
            if Y(r) < desde: continue
            for e in range(3):
                p, f = struct.unpack_from('<II', r, 4 + 26 * e)
                t = club24.get(p - 1)
                if t in tu24: v[tu24[t]][f] += 1
    out = {}
    for u, c in v.items():
        f, n = c.most_common(1)[0]
        if n >= 2 and n > 0.5 * sum(c.values()): out[u] = f
    return out

def uids_personas(path_db, csv_jug, desfase_ficha, ids_extra):
    """{pid: uid}: jugadores (ficha [pid][uid][uid] en pos_bloque+desfase) + personas premiadas (registros tipo 1/2/16/19)"""
    import csv, mmap, fm_personas as FP
    f = open(path_db, 'rb'); m = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ); out = {}; club = {}
    for r in csv.DictReader(open(csv_jug, encoding='utf-8-sig')):
        try: pid = int(r['id_jugador']); pb = int(r['pos_bloque'])
        except ValueError: continue
        try: club[pid] = int(r['id_club'])
        except ValueError: pass
        a, b, c = struct.unpack_from('<III', m, pb + desfase_ficha)
        if a == pid and b == c: out[pid] = b
    for i, cn in FP.mapa(path_db, ids_extra).items():
        c = collections.Counter({u: n for (u, b), n in cn.items() if b in (1, 2, 16, 19)})
        if c: out.setdefault(i, c.most_common(1)[0][0])
    return out, club
def ids_premiados(ls, dt):
    L, _, _, d0 = T.leer(ls)
    return {struct.unpack_from('<I', dt, d0 + o + 4 + 26 * e)[0] - 1 for l in L for o in l for e in range(3)} - {0xfffffffe}
