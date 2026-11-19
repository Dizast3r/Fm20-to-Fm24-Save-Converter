"""Final standings of the last season: the league tables of every competition file (rgman/comp_N.dat) are rows of a
fixed size starting with the team id, in position order (FM20 218 bytes, FM24 429). The FM24 template has its own
season, so a club can finish anywhere (Espanyol 18th in the 2031 template, champion in FM20). The FM24 rows keep
their statistics (points, wins...) but the team ids are reordered so that the clubs end in their FM20 positions."""
import struct, collections, sys
import fm_ligas as LG
def tablas(d, ids, R, minimo=4):
    """[(position, [team ids])] of the tables of rows of R bytes in d"""
    pos = LG.posiciones(d, ids); ps = set(pos); out = []
    for p in pos:
        if p - R in ps: continue
        n = 0
        while p + R * n in ps: n += 1
        if n < minimo: continue
        ts = [struct.unpack_from('<I', d, p + R * i)[0] for i in range(n)]
        if len(set(ts)) == n: out.append((p, ts))
    return out
def paso(src20, entrada, salida):
    import time, fmsave, fmcontenedor as C, fm_uids as U
    t0 = time.time(); est = collections.Counter()
    S20 = fmsave.Save(src20); m20 = S20.read_mmap('game_db.dat')
    E = C.Contenedor(entrada); dm = E.read('game_db.dat')
    t20 = LG.team_zone(m20); t24 = LG.team_zone(dm)
    U.traducir_zona(t20, U.traduccion(m20, dm)[0])
    u24 = {}
    for t, v in t24.items(): u24.setdefault(v['uid'], t)
    a24 = {t20t: u24.get(v['uid']) for t20t, v in t20.items()}   # FM20 team -> FM24 team
    del dm
    ids20 = set(t20); ids24 = set(t24)
    # FM20 tables: (file, position) -> order of FM24 team ids
    f20 = []
    for e in S20.sub.get('rgman', []):
        n = e['name']
        if not (n.startswith('comp_') and n[5:-4].isdigit()): continue
        d = S20.read(n, 'rgman')
        for p, ts in tablas(d, ids20, 218):
            f20.append([a24.get(t) for t in ts])
    indice = collections.defaultdict(list)   # FM24 team -> FM20 tables with it
    for k, o in enumerate(f20):
        for t in o:
            if t is not None: indice[t].append(k)
    nuevos = {}
    for g, n in E.names():
        if g != b'rgman' or not (n.startswith('comp_') and n[5:-4].isdigit()): continue
        d = bytearray(E.read(n, 'rgman')); cambio = False
        for p, ts in tablas(d, ids24, 429):
            s = set(ts)
            c = collections.Counter(k for t in ts for k in indice.get(t, ()))
            mejor = f20[min(c, key=lambda k: (-c[k], k))] if c else None
            if not mejor or len(s & set(mejor)) < max(4, 0.75 * len(ts)): est['tabla sin pareja en FM20'] += 1; continue
            comunes = [t for t in mejor if t in s]           # FM20 order
            sitios = [i for i, t in enumerate(ts) if t in set(comunes)]
            nuevo = list(ts)
            for i, t in zip(sitios, comunes): nuevo[i] = t
            if nuevo != ts:
                for i, t in enumerate(nuevo): struct.pack_into('<I', d, p + 429 * i, t)
                cambio = True; est['tablas reordenadas'] += 1
            else: est['tablas ya en orden'] += 1
        if cambio: nuevos[('rgman', n)] = bytes(d)
    E.escribir(salida, nuevos)
    print('clasificaciones: tablas FM20 %d | ' % len(f20) + ' | '.join('%s %d' % kv for kv in est.items()) + ' | %.0fs' % (time.time() - t0))
if __name__ == '__main__':
    a = sys.argv[1:]; paso(a[0], a[1], a[2])
