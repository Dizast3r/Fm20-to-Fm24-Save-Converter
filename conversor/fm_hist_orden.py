"""asigna bloques de tc_league_history a equipos.
Los bloques van en orden de id de equipo (solo equipos con historial). Para los bloques 'activos' (ultima temporada reciente)
la competicion de la ultima fila coincide con la division actual o anterior del equipo: se buscan todos los pares
(bloque, equipo) compatibles y se toma la cadena creciente mas larga (LIS) en ambos indices."""
import struct, bisect
def ultima(b):
    x = max(b, key=lambda r: struct.unpack_from('<H', r, 0)[0])
    return struct.unpack_from('<H', x, 0)[0], struct.unpack_from('<H', x, 2)[0]
def asignar(bloques, ts, anio_min):
    porcomp = {}
    for t, v in ts.items():
        for c in {v['div'] & 0xffff, v['last'] & 0xffff}:
            if v['div'] < 0x10000 or v['last'] < 0x10000: porcomp.setdefault(c, []).append(t)
    pares = []
    for i, b in enumerate(bloques):
        if not b: continue
        y, c = ultima(b)
        if y < anio_min: continue
        for t in sorted(porcomp.get(c, ()), reverse=True): pares.append((i, t))
    # LIS estricta en t (pares ya ordenados por i asc, t desc dentro de i)
    tails = []; tidx = []; prev = [None] * len(pares)
    for k, (i, t) in enumerate(pares):
        p = bisect.bisect_left(tails, t)
        if p == len(tails): tails.append(t); tidx.append(k)
        else: tails[p] = t; tidx[p] = k
        prev[k] = tidx[p - 1] if p else None
    k = tidx[-1] if tidx else None; asig = {}
    while k is not None: asig[pares[k][0]] = pares[k][1]; k = prev[k]
    return asig

def anclar(b20, ts20, firma, a24, u24, anio_min):
    """bloque FM20 -> uid. Anclas: firma (bloque20->bloque24) + orden FM24 (bloque24->uid). Los huecos entre anclas se
    rellenan con la LIS de pares compatibles restringida al hueco."""
    t_por_uid = {}
    for t, v in ts20.items(): t_por_uid.setdefault(v['uid'], t)
    anc = {}
    for i, j in firma.items():
        if j in a24:
            t = t_por_uid.get(u24[a24[j]])
            if t is not None: anc[i] = t
    # quitar anclas no monotonas (LIS sobre anclas)
    ks = sorted(anc); tails = []; tidx = []; prev = [None] * len(ks)
    for k, i in enumerate(ks):
        p = bisect.bisect_left(tails, anc[i])
        if p == len(tails): tails.append(anc[i]); tidx.append(k)
        else: tails[p] = anc[i]; tidx[p] = k
        prev[k] = tidx[p - 1] if p else None
    k = tidx[-1] if tidx else None; buenas = {}
    while k is not None: buenas[ks[k]] = anc[ks[k]]; k = prev[k]
    res = {i: ts20[t]['uid'] for i, t in buenas.items()}
    lim = [(-1, -1)] + sorted(buenas.items()) + [(len(b20), 1 << 30)]
    for (i1, t1), (i2, t2) in zip(lim, lim[1:]):
        if i2 - i1 <= 1: continue
        sub = {t: v for t, v in ts20.items() if t1 < t < t2}
        if not sub: continue
        loc = asignar([b20[i] if i1 < i < i2 else [] for i in range(len(b20))], sub, anio_min)
        for i, t in loc.items():
            if i1 < i < i2: res[i] = sub[t]['uid']
    return res, len(anc), len(buenas)
