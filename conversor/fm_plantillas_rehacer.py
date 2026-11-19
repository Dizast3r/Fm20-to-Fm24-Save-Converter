"""Squad lists after the transplant: every team record keeps [ff ff ff ff][n u16][n x pid+1] (fm_plantillas.squad_of).
The transplant edits players one by one, and a list can end with players that are no longer there (a FM24 player
whose record now holds a FM20 player of another club) or without players that are (FM20 Espanyol: 86 in the first
team list, 119 after the conversion). Each list touched by the conversion is rebuilt from the players themselves:
the players whose team is that team, plus, for the club's own players loaned out (contract with the team, playing
for a team that is not one of its reserve or youth teams). Entries that are not players (not in the export) stay."""
import struct, sys, csv, collections, re, os
import fm_plantillas as PL
def cabeceras(m, ts):
    """{team: position of its record} for the teams of ts in the team table (fm_equipos.tabla). The first match of
    the header pattern is not reliable: AY took records of other kinds for 40 teams and wrote squad lists into them."""
    import fm_equipos as EQ
    t = EQ.tabla(m); return {k: t[k] for k in ts if k in t}
LISTA = re.compile(rb'[\x00-\x0f]\xff\xff\xff\xff', re.S)
def ids_validos(m, q):
    n = struct.unpack_from('<H', m, q)[0]
    if n > 300: return None
    ids = struct.unpack_from('<%dI' % n, m, q + 2)
    return (q, n, ids) if len(set(ids)) == n and all(0 < i < 3000000 for i in ids) else None
def lista(m, p):
    """(position of n, n, ids) of the squad list of the team record at p: [n u16][n x pid+1], 46 bytes after the
    record start in a club team (0a: every record of FM20 and FM24 2031), after [byte][ff ff ff ff] 95 to 115 bytes
    after it in a national team (0b). An empty list (n = 0) is a list: fm_plantillas.squad_of skips it and takes a
    later id list of the record, which is not the squad."""
    if m[p + 12] == 0x0a: return ids_validos(m, p + 46)
    for x in LISTA.finditer(m, p + 80, p + 120):
        r = ids_validos(m, x.end())
        if r: return r
    return None
def paso(src20, entrada, salida, w):
    import time, fm_export as X, fmcontenedor as C
    t0 = time.time()
    csvp = w + '/convertidos.csv'
    if not os.path.exists(csvp) or os.path.getmtime(csvp) < os.path.getmtime(entrada): X.main(entrada, csvp)
    r = csv.reader(open(csvp, encoding='utf-8-sig')); h = next(r)
    I = {k: h.index(k) for k in ('id_jugador', 'id_club', 'id_club_contrato', 'pos_bloque', 'pos_nombre')}
    E = C.Contenedor(entrada); m = E.read('game_db.dat')
    eq = {}; con = {}; todos = {}
    for row in r:
        p = int(row[I['id_jugador']])
        eq[p] = int(row[I['id_club']]) if row[I['id_club']] else None
        con[p] = int(row[I['id_club_contrato']]) if row[I['id_club_contrato']] else None
        # every contract of the player ([pid+1][team] between his block and his name): the parent club of a loan is
        # not always the contract next to the name (FM20 and FM24 keep them in different order)
        key = struct.pack('<I', p + 1); k = int(row[I['pos_bloque']]); o = int(row[I['pos_nombre']]); cs = []
        while True:
            k = m.find(key, k + 1, o)
            if k < 0: break
            cs.append(struct.unpack_from('<I', m, k + 4)[0])
        todos[p] = cs
    print('exportados %d | %.0fs' % (len(eq), time.time() - t0), flush=True)
    hosts = set()
    for tok in open(w + '/pares.txt').read().split(): hosts.add(int(tok.split(':')[1]))
    por_eq = collections.defaultdict(list)
    for p, t in eq.items():
        if t is not None: por_eq[t].append(p)
    padre = {}   # reserve / youth team -> team of the club most of its players have a contract with
    for t, ps in por_eq.items():
        c = collections.Counter(con[p] for p in ps if con[p] is not None)
        if c:
            k, n = c.most_common(1)[0]
            if k != t and n > len(ps) / 2: padre[t] = k
    fuera = collections.defaultdict(list)   # loaned out: contract with T, playing for a team of another club
    for p, t in eq.items():
        if t is None: continue
        for k in set(todos[p]):
            if k != t and k != 0xffffffff and padre.get(t) != k and padre.get(k) != t: fuera[k].append(p)
    objetivo = {eq[p] for p in hosts if eq.get(p) is not None} | {k for p in hosts for k in todos.get(p, ()) if k != 0xffffffff}
    est = collections.Counter(); edits = []
    # FM20 lists, translated: the squad of each team as it was in FM20 (loaned-out players registered with the B team
    # stay in the B list...), plus the FM24 players of that team that were not used, plus non-player entries
    import fmsave, fm_ligas as LG, fm_uids as U, fm_equipos_club as EC
    m20 = fmsave.Save(src20).read_mmap('game_db.dat')
    t20 = LG.team_zone(m20); t24 = LG.team_zone(m)
    tr = U.traduccion(m20, m)[0]
    sec = EC.mapa_secundarios(m20, m, t20, t24, tr)
    U.traducir_zona(t20, tr)
    u24 = {}
    for t, v in t24.items(): u24.setdefault(v['uid'], t)
    a24 = {t: u24.get(v['uid']) for t, v in t20.items()}; a24.update(sec)
    P = {}
    for tok in open(w + '/pares.txt').read().split():
        v = tok.split(':'); P[int(v[0])] = int(v[1])
    inv = {}
    for a, b in a24.items():
        if b is not None and b in objetivo: inv.setdefault(b, a)
    c20 = cabeceras(m20, set(inv.values()))
    lista20 = {}
    for b, a in inv.items():
        if a in c20:
            sq = lista(m20, c20[a])
            if sq is not None: lista20[b] = [i - 1 for i in sq[2]]
    print('listas FM20 emparejadas %d | %.0fs' % (len(lista20), time.time() - t0), flush=True)
    cabs = cabeceras(m, objetivo)
    for t in objetivo:
        c = cabs.get(t)
        if c is None: est['equipo no localizado'] += 1; continue
        sq = lista(m, c)
        if sq is None: est['sin lista'] += 1; continue
        q, n, ids = sq
        antes = [i - 1 for i in ids]
        if t in lista20:
            quiero = [P[p] for p in lista20[t] if p in P] + [p for p in por_eq.get(t, []) if p not in hosts]
            est['desde la lista FM20'] += 1
        else: quiero = por_eq.get(t, []) + fuera.get(t, [])
        qs = set(quiero)
        nuevo = [p for p in antes if p in qs or p not in eq] + [p for p in quiero if p not in set(antes)]
        if nuevo != antes:
            edits.append((q, 2 + 4 * n, struct.pack('<H', len(nuevo)) + struct.pack('<%dI' % len(nuevo), *[p + 1 for p in nuevo])))
            est['listas rehechas'] += 1; est['quitados'] += sum(1 for p in antes if p in eq and p not in qs)
            est['añadidos'] += sum(1 for p in quiero if p not in set(antes))
        else: est['sin cambios'] += 1
    edits.sort(); parts = []; cur = 0; mv = memoryview(m)
    for p, ln, new in edits:
        if p < cur: est['solapadas'] += 1; continue
        parts.append(mv[cur:p]); parts.append(new); cur = p + ln
    parts.append(mv[cur:]); nm = b''.join(parts); del parts, mv, m
    E.escribir(salida, {('', 'game_db.dat'): nm})
    print('listas de plantilla: ' + ' | '.join('%s %d' % kv for kv in est.items()) + ' | %.0fs' % (time.time() - t0))
if __name__ == '__main__':
    a = sys.argv[1:]; paso(a[0], a[1], a[2], a[3])
