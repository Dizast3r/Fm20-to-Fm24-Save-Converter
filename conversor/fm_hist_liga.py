"""historial de ligas de los clubes (tc_league_history): copia las temporadas jugadas en FM20 a la partida FM24.
uso: fm_hist_liga.py fm20.fm plantilla24.fm entrada24.fm salida.fm [desplazar_anios]
 - plantilla24: la FM24 original (para identificar bloques por equipo con su game_db sin tocar)
 - entrada24: la partida ya convertida (se reescribe solo tc_league_history_dt.cmt)
Identificacion: FM20 bloque <-> FM24 bloque por filas historicas iguales (<=2018); FM24 bloque -> equipo por orden;
FM20 bloque sin firma -> uid por orden entre anclas. Las filas se sobrescriben en su sitio (año destino = año FM20 + desplazamiento);
las temporadas que no existen en FM24 se añaden al final del _dt y se insertan en la lista del club en orden de año (HIST_ANADIR=0 lo desactiva)."""
import sys, os, struct, mmap, collections, tempfile, json
import fmsave, fmcontenedor as C, fm_historial as H, fm_hist_orden as O, fm_ligas as LG
Y = lambda x: struct.unpack_from('<H', x, 0)[0]
CO = lambda x: struct.unpack_from('<H', x, 2)[0]
def firma(b20, b24, hasta=2018):
    key = lambda x: (x[0:2], x[4:6], x[12:24]); idx = collections.defaultdict(set)
    for j, bl in enumerate(b24):
        for x in bl:
            if Y(x) <= hasta: idx[key(x)].add(j)
    m = {}
    for i, bl in enumerate(b20):
        ks = [key(x) for x in bl if Y(x) <= hasta]
        if not ks: continue
        v = collections.Counter(j for k in ks for j in idx.get(k, ()))
        top = v.most_common(2) + [(None, 0), (None, 0)]
        if top[0][1] >= max(2, 0.5 * len(ks)) and top[0][1] > top[1][1]: m[i] = top[0][0]
    return m
def mapa_comps(b20, b24, m, hasta=2018):
    c = collections.defaultdict(collections.Counter)
    for i, j in m.items():
        d24 = {(Y(x), x[6]): CO(x) for x in b24[j] if Y(x) <= hasta}
        for x in b20[i]:
            k = (Y(x), x[6])
            if k in d24: c[CO(x)][d24[k]] += 1
    return {a: v.most_common(1)[0][0] for a, v in c.items()}
def gamedb(save):
    fd, p = tempfile.mkstemp(); os.write(fd, save); os.close(fd)
    f = open(p, 'rb'); return mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ), p
PARTE = os.environ.get('HISTORIAL_PARTE', 'todo')   # todo | liga (all but the players) | jugadores (players only)
def main_jugadores(src20, plantilla, entrada, salida, desp):
    """player career history and injuries only (a long template does not fit in memory with everything else):
    uses the maps left by the 'liga' part in hist_mapas.pkl"""
    import fm_hist_jugadores as HJ, pickle
    W = os.environ.get('TRABAJO', 'trabajo')
    s20 = fmsave.Save(src20); E = C.Contenedor(entrada); nuevos = {}
    hj = json.load(open(W + '/historial_jugadores.json')); mp = pickle.load(open(W + '/hist_mapas.pkl', 'rb'))
    nl, nd, eh = HJ.transferir(s20.read('player_stats_hist_ls.dat', 'rgman'), s20.read('player_stats_hist_dt.cmt'),
                               E.read('player_stats_hist_ls.dat', 'rgman'), E.read('player_stats_hist_dt.cmt'),
                               hj['listas'], mp['tu20'], mp['tu24'], mp['cm'], desp, ps20=s20.read('player_stats.dat', 'rgman'))
    nuevos[('rgman', 'player_stats_hist_ls.dat')] = nl; nuevos[('', 'player_stats_hist_dt.cmt')] = nd
    print('historial de jugadores: ' + ' | '.join('%s %d' % kv for kv in eh.items()))
    if hj.get('lesiones'):
        import fm_lesiones as LS
        nl, nd, el = LS.transferir(s20.read('injury_histories_ls.dat'), s20.read('injury_histories_dt.cmt'),
                                   E.read('injury_histories_ls.dat'), E.read('injury_histories_dt.cmt'), hj['lesiones'], desp)
        nuevos[('', 'injury_histories_ls.dat')] = nl; nuevos[('', 'injury_histories_dt.cmt')] = nd
        print('lesiones: ' + ' | '.join('%s %d' % kv for kv in el.items()))
    # database history (seasons before the game): fm_pl_hist
    try:
        lsp = E.read('pl_hist_ls.dat'); dtp = E.read('pl_hist_dt.cmt')
    except Exception: lsp = None
    if lsp is not None and len(lsp) > 1000:
        import fm_pl_hist as PH, fm_tad as TT, csv
        def uids(path, m, d):
            r = csv.reader(open(path, encoding='utf-8-sig')); h = next(r); i, j = h.index('id_jugador'), h.index('pos_bloque'); out = {}
            for row in r:
                try: pid, pb = int(row[i]), int(row[j])
                except ValueError: continue
                a, b, c = struct.unpack_from('<III', m, pb + d)
                if a == pid and b == c: out[pid] = b
            return out
        m24 = fmsave.Save(plantilla).read_mmap('game_db.dat'); m20 = s20.read_mmap('game_db.dat')
        hu = uids(W + '/base.csv', m24, -42); u20 = uids(W + '/fm20.csv', m20, -38)
        pares = []
        for tok in open(W + '/pares.txt').read().split():
            v = tok.split(':'); pares.append((int(v[0]), int(v[1])))
        nl = len(TT.leer(lsp)[0])
        tab = PH.tabla(m24, nl, [hu[h] for _, h in pares[:200] if h in hu])
        if tab:
            nl_, nd_, ep = PH.transferir(lsp, dtp, pares, hu, u20, tab, 2019 + desp)
            nuevos[('', 'pl_hist_ls.dat')] = nl_; nuevos[('', 'pl_hist_dt.cmt')] = nd_
            print('historial de base de datos (pl_hist): tabla %d | ' % len(tab) + ' | '.join('%s %d' % kv for kv in ep.items()))
        else: print('historial de base de datos (pl_hist): tabla no localizada')
    E.escribir(salida, nuevos)
    return {}
def main(src20, plantilla, entrada, salida, desp):
    if PARTE == 'jugadores': return main_jugadores(src20, plantilla, entrada, salida, desp)
    s20 = fmsave.Save(src20)
    ls20 = s20.read('tc_league_history_ls.dat'); dt20 = s20.read('tc_league_history_dt.cmt')
    b20 = H.leer(ls20, dt20)[0]
    P = C.Contenedor(plantilla)
    ls24 = P.read('tc_league_history_ls.dat'); dt24p = P.read('tc_league_history_dt.cmt')
    import fm_tad as T
    off24, cab24, cola24, d0 = T.leer(ls24)
    b24 = [[bytes(dt24p[d0 + x:d0 + x + 24]) for x in o] for o in off24]
    def gdb(sv):   # decompressed once to the cache and memory-mapped (a long template's game_db does not fit twice in memory)
        p = sv.cache_path('game_db.dat'); f = open(p, 'rb'); return mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ), p
    m20, p20 = gdb(s20); m24, p24 = gdb(fmsave.Save(plantilla))
    ts20 = LG.team_zone(m20); ts24 = LG.team_zone(m24)
    import fm_uids as U   # clubs whose uid changed between FM20 and FM24
    tr_uid, est_uid = U.traduccion(m20, m24); U.traducir_zona(ts20, tr_uid)
    print('clubes FM20->FM24: ' + ' | '.join('%s %d' % kv for kv in est_uid.items()))
    fin20 = max(Y(x) for b in b20 for x in b); fin24 = max(Y(x) for b in b24 for x in b if Y(x) < 2100)
    sm = firma(b20, b24); cm = mapa_comps(b20, b24, sm)
    a24 = O.asignar(b24, ts24, fin24 - 1); u24 = {t: ts24[t]['uid'] for t in a24.values()}
    uid20, na, nb = O.anclar(b20, ts20, sm, a24, u24, fin20 - 1)
    blk24 = {}
    for j, t in a24.items(): blk24.setdefault(ts24[t]['uid'], j)
    E = C.Contenedor(entrada)
    dt = bytearray(E.read('tc_league_history_dt.cmt'))
    assert E.read('tc_league_history_ls.dat') == ls24, 'la entrada debe tener el mismo historial que la plantilla'
    est = collections.Counter(); hechos = {}; listas = [list(o) for o in off24]; extra = bytearray()
    AÑADIR = os.environ.get('HIST_ANADIR', '1') == '1'
    for i, b in enumerate(b20):
        nuevas = [x for x in b if Y(x) >= 2020]
        if not nuevas: continue
        j = sm.get(i)
        if j is None and i in uid20: j = blk24.get(uid20[i])
        if j is None: est['club sin pareja'] += 1; continue
        est['clubes'] += 1
        sitio = {(Y(x), x[6]): o for x, o in zip(b24[j], off24[j])}
        for x in nuevas:
            yt = Y(x) + desp; o = sitio.get((yt, x[6]))
            c = cm.get(CO(x))
            if c is None: est['competicion sin equivalente'] += 1; continue
            fila = bytearray(x); struct.pack_into('<HH', fila, 0, yt, c)
            if o is None:
                if not AÑADIR: est['temporada sin fila en FM24'] += 1; continue
                o = len(dt) - d0 + len(extra); extra += fila
                l = listas[j]; k = 0
                while k < len(l) and Y(dt[d0 + l[k]:d0 + l[k] + 2] if l[k] < len(dt) - d0 else extra[l[k] - (len(dt) - d0):][:2]) <= yt: k += 1
                l.insert(k, o); est['temporadas añadidas'] += 1
            else:
                dt[d0 + o:d0 + o + 24] = fila; est['temporadas sobrescritas'] += 1
            hechos.setdefault(i, []).append((Y(x), yt, x[4] + 1))
    nuevos = {('', 'tc_league_history_dt.cmt'): bytes(dt + extra)}
    if extra: nuevos[('', 'tc_league_history_ls.dat')] = T.escribir(cab24, listas, cola24)
    # historial de competiciones (campeones, subcampeones... de cada temporada) -> palmares
    import fm_hist_comp as HC, fm_uids as U
    lc24 = P.read('comp_history_ls.dat', 'rgman'); dc24 = P.read('comp_history_dt.cmt')
    assert E.read('comp_history_ls.dat', 'rgman') == lc24
    import fm_estadios as ES
    tu20 = {t: U.aplicar(tr_uid, u) for t, u in U.mapa(m20).items()}; tu24 = U.mapa(m24); es20 = ES.mapa(m20); es24 = ES.mapa(m24)
    lc20 = s20.read('comp_history_ls.dat', 'rgman'); dc20 = s20.read('comp_history_dt.cmt')
    ult20 = HC.filas_db(m20, 20, range(2020, 2040))   # FM20's last finished season(s), still inside its game_db
    nls, ndt, ec, cpar = HC.transferir(lc20, dc20, lc24, dc24, tu20, tu24, desp, e20=es20, e24=es24, extra20=ult20)
    import pickle
    pickle.dump(dict(tu20=tu20, tu24=tu24, es20=es20, es24=es24, cpar=cpar, cm=cm), open(os.environ.get('TRABAJO', 'trabajo') + '/hist_mapas.pkl', 'wb'))
    nuevos[('', 'comp_history_dt.cmt')] = ndt
    if nls != lc24: nuevos[('rgman', 'comp_history_ls.dat')] = nls
    print('historial de competiciones: ' + ' | '.join('%s %d' % kv for kv in ec.items()))
    # premios por temporada
    import fm_hist_premios as HP
    W = os.environ.get('TRABAJO', 'trabajo')
    la20 = s20.read('award_year_hist_ls.dat'); da20 = s20.read('award_year_hist_dt.cmt')
    la24 = P.read('award_year_hist_ls.dat'); da24 = P.read('award_year_hist_dt.cmt')
    assert E.read('award_year_hist_ls.dat') == la24
    pu20, _ = HP.uids_personas(p20, W + '/fm20.csv', -38, HP.ids_premiados(la20, da20))
    pu24, club24 = HP.uids_personas(p24, W + '/base.csv', -42, HP.ids_premiados(la24, da24))
    campo = {u: u + 1 for u in set(tu24.values())}   # el campo club de los premios es uid del club + 1
    nla, nda, ea, apar = HP.transferir(la20, da20, la24, da24, pu20, pu24, HP.leer_pares(W + '/pares.txt'), tu20, tu24, campo, desp)
    nuevos[('', 'award_year_hist_dt.cmt')] = nda
    if nla != la24: nuevos[('', 'award_year_hist_ls.dat')] = nla
    print('premios: ' + ' | '.join('%s %d' % kv for kv in ea.items()))
    # player career history
    if os.path.exists(W + '/historial_jugadores.json'):
        import fm_hist_jugadores as HJ
        hj = json.load(open(W + '/historial_jugadores.json'))
    if os.path.exists(W + '/historial_jugadores.json') and PARTE == 'todo':
        nl, nd, eh = HJ.transferir(s20.read('player_stats_hist_ls.dat', 'rgman'), s20.read('player_stats_hist_dt.cmt'),
                                   E.read('player_stats_hist_ls.dat', 'rgman'), E.read('player_stats_hist_dt.cmt'),
                                   hj['listas'], tu20, tu24, cm, desp, ps20=s20.read('player_stats.dat', 'rgman'))
        nuevos[('rgman', 'player_stats_hist_ls.dat')] = nl; nuevos[('', 'player_stats_hist_dt.cmt')] = nd
        print('historial de jugadores: ' + ' | '.join('%s %d' % kv for kv in eh.items()))
    if os.path.exists(W + '/historial_jugadores.json'):
        if hj.get('lesiones') and PARTE == 'todo':
            import fm_lesiones as LS
            nl, nd, el = LS.transferir(s20.read('injury_histories_ls.dat'), s20.read('injury_histories_dt.cmt'),
                                       E.read('injury_histories_ls.dat'), E.read('injury_histories_dt.cmt'), hj['lesiones'], desp)
            nuevos[('', 'injury_histories_ls.dat')] = nl; nuevos[('', 'injury_histories_dt.cmt')] = nd
            print('lesiones: ' + ' | '.join('%s %d' % kv for kv in el.items()))
        if hj.get('hitos'):
            import fm_tad as TT, pickle
            # competitions: unique ids of the competition records, then league codes and comp_history pairing;
            # awards: award_year_hist pairing
            import fm_comps_uid as CU
            c24 = CU.pares(m20, m24); dif = sum(1 for k, v in cm.items() if k in c24 and c24[k] != v)
            for k, v in cm.items(): c24.setdefault(k, v)
            L20c, _, _, x0 = TT.leer(lc20); L24c, _, _, y0 = TT.leer(lc24)
            for i_, j_ in cpar.items():
                if L20c[i_] and L24c[j_]: c24.setdefault(struct.unpack_from('<I', dc20, x0 + L20c[i_][0])[0], struct.unpack_from('<I', dc24, y0 + L24c[j_][0])[0])
            L20a, _, _, x0 = TT.leer(la20); L24a, _, _, y0 = TT.leer(la24); a24 = {}
            for i_, j_ in apar.items():
                if L20a[i_] and L24a[j_]: a24[struct.unpack_from('<H', da20, x0 + L20a[i_][0] + 2)[0]] = struct.unpack_from('<H', da24, y0 + L24a[j_][0] + 2)[0]
            # the milestones themselves are converted in the 'temporada' step (fm_hist_temporada.py)
            mp = pickle.load(open(W + '/hist_mapas.pkl', 'rb')); mp.update(c24=c24, a24=a24)
            pickle.dump(mp, open(W + '/hist_mapas.pkl', 'wb'))
            print('mapas para hitos: premios %d | competiciones %d (codigos de liga distintos %d)' % (len(a24), len(c24), dif))
    E.escribir(salida, nuevos)
    pass   # the game_db copies stay in the cache
    print('historial de liga: bloques FM20 %d | firma %d | anclas %d/%d | comps mapeadas %d' % (len(b20), len(sm), nb, na, len(cm)))
    print('  ' + ' | '.join('%s %d' % kv for kv in est.items()))
    return hechos
if __name__ == '__main__':
    a = sys.argv[1:]
    desp = int(a[4]) if len(a) > 4 else json.load(open('trabajo/desfase.json'))['desplazar_anios']
    h = main(a[0], a[1], a[2], a[3], desp)
    print('Espanyol (bloque 967):', h.get(967))
