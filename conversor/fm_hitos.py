"""Milestones (person_record_history): awards, records, debuts, transfers... one list per person.
FM20 row (44): [00][team u32][u8][team2 u32][person u32][comp u16][award u16][date][A][B][C][D][E u32][type u8][flag u8]
FM24 row (42): [date][A][B][C][D][E u32][type u8][flag u8][00][team u32][person u32][comp u16] + 5 bytes:
               [00][team2 u32] (ff.. when none) or, for award rows, [award u16][00 00 00]
team = the player's team, team2 = the other team (opponent, buying/selling club), person = the player himself.
Team, person, competition and award ids are translated; years inside A..E and the date are shifted.
Rows whose award, team or competition has no FM24 equivalent are dropped."""
import struct, collections
import fm_tad as T
def anio(v, desp): return v + desp if 1990 <= v <= 2100 else v
def convertir(r, desp, t24, p24, c24, a24, est=None):
    team, team2, pers = struct.unpack_from('<I', r, 1)[0], struct.unpack_from('<I', r, 6)[0], struct.unpack_from('<I', r, 10)[0]
    comp, award = struct.unpack_from('<HH', r, 14); d, y = struct.unpack_from('<HH', r, 18)
    A = [anio(v, desp) for v in struct.unpack_from('<5I', r, 22)]; tipo, flag = r[42], r[43]
    if award != 0xffff:
        award = a24.get(award)
        if award is None: return None
    if 1900 < y < 2100:
        y += desp
        if (d & 0x1ff) == 366 and not (y % 4 == 0 and (y % 100 or y % 400 == 0)): d -= 1
    # a row that names a team or competition FM24 does not have would show "team#2" / "comp#1": drop it
    t1 = t24(team) if team != 0xffffffff else team
    t2 = t24(team2) if team2 != 0xffffffff else team2
    c = c24.get(comp, 0xffff) if comp != 0xffff else comp
    falta = None
    if (team != 0xffffffff and t1 == 0xffffffff) or (team2 != 0xffffffff and t2 == 0xffffffff): falta = 'equipo'
    elif comp != 0xffff and c == 0xffff: falta = 'competicion'
    if falta:
        if est is not None: est['hitos descartados (%s sin equivalente)' % falta] += 1
        return False
    if award != 0xffff: cola = struct.pack('<HBH', award, 0, 0)          # as FM24 writes it
    else: cola = struct.pack('<BI', 0, t2)
    return struct.pack('<HH5IBBBIIH', d, y, *A, tipo, flag, 0, t1,
                       p24(pers) if pers != 0xffffffff else 0xffffffff, c) + cola
def transferir(ls20, dt20, ls24, dt24, mapa, desp, t24, p24, c24, a24):
    L20, _, _, a0 = T.leer(ls20); L24, cab, cola, b0 = T.leer(ls24); R20 = T.tam_fila(ls20)
    dt = bytearray(dt24); listas = [list(l) for l in L24]; est = collections.Counter()
    for t, v in mapa:
        if v >= len(L20): continue
        offs = []
        for o in L20[v]:
            r = convertir(dt20[a0 + o:a0 + o + R20], desp, t24, p24, c24, a24, est)
            if r is None: est['hitos sin premio equivalente'] += 1; continue
            if r is False: continue
            offs.append(len(dt) - b0); dt += r
        while len(listas) <= t: listas.append([])
        listas[t] = offs; est['personas'] += 1; est['hitos'] += len(offs)
    return T.escribir(cab, listas, cola), bytes(dt), est

def premios_extra(uso20, tabla24, c24, a24, margen=12):
    """Awards that the award_year_hist pairing could not match (team of the week, monthly awards...).
    uso20: {award: Counter((type, flag, comp))} of FM20; tabla24: {award: (type, flag, comp)} of FM24 (data/fm24_awards.json).
    An FM20 award goes to the FM24 award used the same way (same type, flag and translated competition): the same id
    when possible (most ids are unchanged), otherwise the closest id within `margen` (some moved by one or two)."""
    por = collections.defaultdict(set)
    for aw, k in tabla24.items(): por[tuple(k[:3])].add(aw)
    usados = set(a24.values()); prop = {}
    for aw, c in uso20.items():
        if aw in a24: continue
        (ty, fl, comp), _ = c.most_common(1)[0]
        k = (ty, fl, 0xffff if comp == 0xffff else c24.get(comp, -1))
        cand = por.get(k, set()) - usados
        if aw in cand: prop[aw] = (0, aw); continue
        d = sorted((abs(x - aw), x) for x in cand)
        if d and d[0][0] <= margen and (len(d) == 1 or d[1][0] > d[0][0]): prop[aw] = d[0]
    mejor = {}
    for aw, (dist, x) in prop.items():
        if x not in mejor or dist < mejor[x][0]: mejor[x] = (dist, aw)
    return {aw: x for x, (dist, aw) in mejor.items()}

def paso(s20, E, W, desp, M):
    """milestones of the converted players; M = hist_mapas.pkl (tu20, tu24, c24, a24). Returns the new files."""
    import json, os, fm_hist_premios as HP, fm24_tabla_premios as TP
    hj = json.load(open(W + '/historial_jugadores.json'))
    if not hj.get('hitos'): return {}
    tu20, tu24, c24, a24 = M['tu20'], M['tu24'], M['c24'], dict(M['a24'])
    inv = {}
    for t_, u_ in sorted(tu24.items()): inv.setdefault(u_, t_)
    def ht24(t_): return inv.get(tu20.get(t_), 0xffffffff)
    pares = HP.leer_pares(W + '/pares.txt')
    def hp24(p_): return pares[p_ - 1] + 1 if p_ - 1 in pares else 0xffffffff
    ls20, dt20 = s20.read('person_record_history_ls.dat'), s20.read('person_record_history_dt.cmt')
    ls24, dt24 = E.read('person_record_history_ls.dat'), E.read('person_record_history_dt.cmt')
    tabla = {int(k): v for k, v in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'fm24_awards.json'))).items()}
    for aw, c in TP.uso(ls24, dt24, 42).items(): tabla.setdefault(aw, c.most_common(1)[0][0])
    extra = premios_extra(TP.uso(ls20, dt20, 44), tabla, c24, a24); a24.update(extra)
    nl, nd, est = transferir(ls20, dt20, ls24, dt24, hj['hitos'], desp, ht24, hp24, c24, a24)
    print('hitos: ' + ' | '.join('%s %d' % kv for kv in est.items()) + ' | premios mapeados %d (por uso %d)' % (len(a24), len(extra)))
    return {('', 'person_record_history_ls.dat'): nl, ('', 'person_record_history_dt.cmt'): nd}
