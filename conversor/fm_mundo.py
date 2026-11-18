#!/usr/bin/env python3
"""fm_mundo.py - prepara la plantilla FM24 con el 'mundo' de la partida FM20 (EXPERIMENTAL):
   divisiones de todos los paises, reputacion de equipos, presupuestos y fin de las cesiones de FM24 en clubes convertidos.
   Uso: fm_mundo.py origen_fm20.fm plantilla_fm24.fm salida.fm  (variables: CSV20, CSV24, CESIONES_EQUIPOS, PRESUPUESTOS=1)"""
import sys, os, re, struct, collections
import numpy as np
from fmsave import Save
import fmcontenedor as FC
import fm_ligas as LG

def team_ids_in(buf, universe):
    a = np.frombuffer(buf, dtype=np.uint8); out = set()
    for off in range(4):
        n = (len(a) - off) // 4
        if n <= 0: continue
        v = np.unique(a[off:off + 4 * n].view('<u4'))
        out |= set(np.intersect1d(v, universe).tolist())
    return out

def plan_divisiones(tb, ts):
    """tb/ts: fichas de equipo (team_zone) de la plantilla y de FM20. Devuelve (deseo, actual, ligas)"""
    u20 = {}
    for t, v in ts.items(): u20.setdefault(v['uid'], v)
    miembros = collections.defaultdict(list)
    for t, v in tb.items(): miembros[v['div']].append(t)
    # codigo FM24 -> codigo FM20: el mismo codigo si comparte >= 3 clubes; si no, el mayoritario (>= 40 %)
    M = {}
    for d, tt in miembros.items():
        if not 4 <= len(tt) <= 40 or d == 0xffffffff: continue
        c = collections.Counter(u20[tb[t]['uid']]['div'] for t in tt if tb[t]['uid'] in u20)
        if not c: continue
        if c.get(d, 0) >= 3: M[d] = (d, 10**6 + c[d]); continue
        top, k = c.most_common(1)[0]
        if top != 0xffffffff and k >= max(3, 0.4 * len(tt)): M[d] = (top, k)
    W = {}
    for d, (c20, k) in M.items():
        if c20 not in W or k > M[W[c20]][1]: W[c20] = d
    return M, W, miembros, u20

def main(src, base, out):
    ssv = Save(src); sm = ssv.read('game_db.dat')
    C = FC.Contenedor(base); dm = bytearray(C.read('game_db.dat'))
    ts = LG.team_zone(sm); tb = LG.team_zone(bytes(dm))
    import fm_uids as U   # clubs whose uid changed between FM20 and FM24
    U.traducir_zona(ts, U.traduccion(sm, bytes(dm))[0])
    M, W, miembros, u20 = plan_divisiones(tb, ts)
    # ficheros de competicion de liga: los que contienen a todos los equipos de la division
    nombres = [n for g, n in C.names() if g == b'rgman' and n.startswith('comp_') and n[5:-4].isdigit()]
    comp = {n: bytearray(C.read(n, 'rgman')) for n in nombres}
    universe = np.array(sorted(tb), dtype=np.uint32)
    contiene = {n: team_ids_in(bytes(b), universe) for n, b in comp.items()}
    ligas = {}
    for d in [d for d, tt in miembros.items() if 4 <= len(tt) <= 40 and d != 0xffffffff]:
        tt = set(miembros[d]); cands = [n for n in nombres if tt <= contiene[n]]
        for n in sorted(cands, key=lambda n: len(contiene[n])):
            prueba = bytearray(comp[n])
            if LG.swap_all_tables(prueba, tt, {}, len(tt)): ligas[d] = n; break
    print('divisiones emparejadas FM24<->FM20:', len(W), '| con fichero de liga localizado:', len(ligas))
    # deseos: division de FM20 traducida a la de FM24 (ligas jugables con fichero y ligas sin partidos)
    cur = {t: v['div'] for t, v in tb.items()}
    want = {}
    for t, v in tb.items():
        if v['uid'] in u20:
            w = W.get(u20[v['uid']]['div'])
            if w is not None: want[t] = w
    mem = collections.defaultdict(set, {d: set(tt) for d, tt in miembros.items()})
    antes = sum(1 for t, w in want.items() if cur[t] == w)
    import fm_clubes as CB
    pais = {c['uid']: c['nation'] for c in CB.clubs(bytes(dm), 8, 60 << 20)}
    pais_t = {t: pais.get(v['uid']) for t, v in tb.items()}
    # clubes sin ficha legible: el pais mayoritario de su division
    for d, tt in miembros.items():
        c = collections.Counter(pais_t[t] for t in tt if pais_t.get(t) is not None)
        if c and c.most_common(1)[0][1] >= 0.8 * sum(c.values()):
            for t in tt:
                if pais_t.get(t) is None: pais_t[t] = c.most_common(1)[0][0]
    import csv as _csv
    njug = collections.Counter(int(x['id_club']) for x in _csv.DictReader(open(os.environ.get('CSV24', 'n24_jugadores.csv'), encoding='utf-8-sig')) if x['id_club'])
    slot = {t: t for t in tb}; cambios = 1; nint = 0; ndir = 0; log = []
    while cambios:
        cambios = 0
        for a in sorted(want):
            Y = want[a]; X = cur[a]
            if X == Y: continue
            if os.environ.get('ALINEAR', '1') != '1': continue
            if X not in ligas and Y not in ligas:      # ninguna de las dos se juega: basta con cambiar el codigo
                if X == 0xffffffff or not 4 <= len(miembros.get(X, ())) <= 40: continue
                if os.environ.get('DIRECTOS', '1') != '1': continue
                mem[X].discard(a); mem[Y].add(a); cur[a] = Y; cambios += 1; ndir += 1; continue
            if os.environ.get('INTERCAMBIOS', '1') != '1': continue
            if X not in ligas or Y not in ligas or pais_t.get(a) is None or njug[a] < 11: continue      # solo entre ligas con partidos y equipos con plantilla
            cand = [b for b in mem[Y] if want.get(b) != Y and pais_t.get(b) == pais_t[a] and njug[b] >= 11]   # y clubes principales del mismo pais
            if not cand: continue
            b = min(cand, key=lambda b: (0 if want.get(b) == X else 1 if b not in want else 2, b))
            log.append((a, b, X, Y))
            mem[X].remove(a); mem[Y].remove(b); mem[Y].add(a); mem[X].add(b)
            cur[a], cur[b] = Y, X; slot[a], slot[b] = slot[b], slot[a]; cambios += 1; nint += 1
    despues = sum(1 for t, w in want.items() if cur[t] == w)
    print('clubes con division deseada:', len(want), '| en su sitio antes:', antes, '| despues:', despues, '| intercambios de plaza:', nint, '| cambios directos (ligas sin partidos):', ndir)
    import pickle; pickle.dump(dict(log=log, ligas=ligas), open(os.environ.get('LOG_MUNDO', '/tmp/mundo_log.pkl'), 'wb'))
    occ = {s: t for t, s in slot.items() if s != t}          # plaza original s -> equipo que la ocupa
    if os.environ.get('SOLO_PLAN'): return
    # 1) fichas de equipo: division actual y anterior de la plaza que ocupan
    orig = {t: bytes(dm[v['divpos']:v['divpos'] + 8]) for t, v in tb.items()}
    for s, t in occ.items(): dm[tb[t]['divpos']:tb[t]['divpos'] + 8] = orig[s]
    for t, v in tb.items():                                  # cambios directos: solo el codigo de division actual
        if t not in occ.values() and cur[t] != v['div'] and t in want: struct.pack_into('<I', dm, v['divpos'], cur[t])
    # 2) clasificaciones y listas de participantes de cada liga
    tocados = set()
    for d, n in ligas.items():
        ids = set(miembros[d]); sw = {s: occ[s] for s in ids if s in occ}
        if not sw: continue
        c = comp[n]; base_b = bytes(c)
        tablas = LG.swap_all_tables(c, ids, sw, len(ids))
        fin = max(st + sz * len(ids) for st, sz in tablas) if tablas else 0
        for s, t in sw.items():
            p = base_b.rfind(struct.pack('<I', s))
            if p > fin: struct.pack_into('<I', c, p, t)
        tocados.add(n)
    # 3) calendario
    fx = bytearray(C.read('fix_man.dat', 'rgman')); nfix = 0
    for x in LG.FIX.finditer(bytes(fx)):
        for g in (1, 2):
            t = struct.unpack('<I', x.group(g))[0]
            if t in occ: struct.pack_into('<I', fx, x.start(g), occ[t]); nfix += 1
    print('ficheros de liga modificados:', len(tocados), '| apariciones cambiadas en el calendario:', nfix)
    import csv
    real20 = {int(x['id_club']) for x in csv.DictReader(open(os.environ.get('CSV20', 'fm20_jugadores.csv'), encoding='utf-8-sig')) if x['id_club']}
    filas24 = list(csv.DictReader(open(os.environ.get('CSV24', 'n24_jugadores.csv'), encoding='utf-8-sig')))
    real24 = {int(x['id_club']) for x in filas24 if x['id_club']}
    # 4) reputacion de cada equipo (solo equipos con jugadores en ambas partidas)
    su = {}
    for t, v in ts.items():
        if t in real20: su.setdefault(v['uid'], v)
    nrep = 0; vistos = set()
    for t, v in sorted(tb.items()):
        if t not in real24 or v['uid'] in vistos or v['uid'] not in su: continue
        o = su[v['uid']]
        r24 = struct.unpack_from('<H', dm, v['pos'] + 15)[0]; r20 = struct.unpack_from('<H', sm, o['pos'] + 15)[0]
        if 0 < r24 <= 10000 and 0 < r20 <= 10000: struct.pack_into('<H', dm, v['pos'] + 15, r20); nrep += 1; vistos.add(v['uid'])
    # 5) presupuestos (fichajes original/actual y salarial), solo clubes con lectura coherente en FM20
    nb = 0
    if os.environ.get('PRESUPUESTOS', '1') == '1':
        import fm_economia as EC
        sal = collections.Counter()
        for x in csv.DictReader(open(os.environ.get('CSV20', 'fm20_jugadores.csv'), encoding='utf-8-sig')):
            if x['id_club'] and x['sueldo_semanal_GBP'] and int(x['id_club']) in ts: sal[ts[int(x['id_club'])]['uid']] += int(x['sueldo_semanal_GBP'])
        b20 = EC.budgets_all(sm, 7); b24 = EC.budgets_all(bytes(dm), 8)
        for u, g24 in b24.items():
            g20 = b20.get(u)
            if not g20 or sal[u] <= 0: continue
            if not 0.5 <= struct.unpack_from('<i', sm, g20['wage'])[0] / sal[u] <= 8: continue
            for k in ('orig', 'cur', 'wage'): dm[g24[k]:g24[k] + 4] = sm[g20[k]:g20[k] + 4]
            nb += 1
    # 6) cesiones de FM24 en los clubes convertidos: terminan al dia siguiente del inicio
    nend = 0
    ef = os.environ.get('CESIONES_EQUIPOS')
    if ef:
        import fm_cesiones as CS
        targets = {int(t) for t in open(ef).read().split()}
        excluir = set(open(os.environ['CESIONES_EXCLUIR']).read().split()) if os.environ.get('CESIONES_EXCLUIR') else set()
        for x in filas24:
            if not x['id_club'] or int(x['id_club']) not in targets or x['id_jugador'] in excluir: continue
            c = int(x['pos_bloque']); o = int(x['pos_nombre']); key = struct.pack('<I', int(x['id_jugador']) + 1); kk = []; q = c
            while True:
                q = dm.find(key, q + 1, o)
                if q < 0: break
                kk.append(q)
            if len(kk) < 2 or dm[kk[0] + 18:kk[0] + 20] != b'\x00\x01' or struct.unpack_from('<I', dm, kk[-1] + 4)[0] != int(x['id_club']): continue
            r = CS.loan_dates(dm, kk[-1])
            if not r: continue
            d0, y0 = struct.unpack_from('<HH', dm, r[1]); d, y = struct.unpack_from('<HH', dm, r[0])
            nd, ny = (d0 & 0x1ff) + 1, y0
            if nd > 365: nd, ny = 1, y0 + 1
            struct.pack_into('<HH', dm, r[0], (d & ~0x1ff) | nd, ny); nend += 1
    print('reputacion copiada en', nrep, 'equipos | presupuestos en', nb, 'clubes | cesiones terminadas:', nend)
    nuevos = {('', 'game_db.dat'): bytes(dm), ('rgman', 'fix_man.dat'): bytes(fx)}
    for n in tocados: nuevos[('rgman', n)] = bytes(comp[n])
    C.escribir(out, nuevos)
    print('escrito', out)

if __name__ == '__main__':
    main(*sys.argv[1:4])
