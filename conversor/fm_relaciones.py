"""Club relationships (legends, icons, favoured personnel, rivals...): the list at the end of every club record,
[u8 count][entries] followed by 00 00.
FM20 entry 12 bytes [id u32][kind u8][00][cat u8][sub u8][level u8][flag u8][u8][ff]
FM24 entry 16 bytes [id u32][00 00 00 00][kind u8][00][cat u8][sub u8][level u8][flag u8][u8][ff]
cat 3 / sub 1: a person (id = pid + 1; kind = role: 1 player, 2 staff, 5 player and manager...). Legends and icons
carry flag 0x4f (legends with the highest level), the favoured personnel are the other high levels.
Other entries (cat 1, cat 3 / sub 2...) point to clubs and other things and are left as they are in FM24."""
import re, struct, sys
import fm_clubnames as N
def _lista(m, fin, ver):
    R = 12 if ver == 7 else 16
    p = fin; n = 0; mejor = None
    while p - R > 0:
        e = m[p - R:p]
        if e[-1] != 0xff or e[R - 7] != 0 or (ver == 8 and e[4:8] != b'\x00\x00\x00\x00'): break
        p -= R; n += 1
        if m[p - 1] == n % 256: mejor = (p - 1, n)
    return mejor
def listas(m, ver):
    """{club uid: (count position, n, [entries])}"""
    R = 12 if ver == 7 else 16
    cabs = N.cabeceras(m); out = {}
    for i, (p, u, _) in enumerate(cabs[:-1]):
        fin = cabs[i + 1][0]
        if m[fin - 2:fin] != b'\x00\x00': continue
        r = _lista(m, fin - 2, ver)
        if r: out.setdefault(u, (r[0], r[1], [bytes(m[r[0] + 1 + R * k:r[0] + 1 + R * (k + 1)]) for k in range(r[1])]))
    return out
def persona(e, ver):
    """(pid + 1) if the entry is a person relationship, else None"""
    k = 4 if ver == 7 else 8
    return struct.unpack_from('<I', e, 0)[0] if e[k + 2] == 3 and e[k + 3] == 1 else None
def a_fm24(e, pid24):
    return struct.pack('<II', pid24, 0) + e[4:]

STUB = re.compile(rb'(?=(.{4})(.{4})\2\x05\x00\x00\x00\x00(.)\x00\x00\x00)', re.S)
def stubs(m):
    """name-only people {pid: (position of the length field, full name)}"""
    out = {}
    for x in STUB.finditer(m):
        L = x.group(3)[0]; q = x.start() + 17; b = m[q + 4:q + 4 + L]
        if L < 3 or b[0] < 0x20 or 0 in b: continue
        try: t = b.decode('utf-8')
        except UnicodeDecodeError: continue
        i, u = struct.unpack('<II', x.group(1) + x.group(2))
        if 0 < u < 0x7fffffff and i < 2000000: out.setdefault(i, (q, t))
    return out
def paso(src20, entrada, salida, pares_txt):
    """replaces the person relationships of every club of `entrada` (converted FM24 save) with the FM20 ones"""
    import os, sys, time, collections
    from fmsave import Save
    import fmcontenedor as C, fm_uids as U, fm_personas as FP, fm_personas_nombre as PN, fm_export as X
    sys.argv = sys.argv[:1]
    import fm_trasplante as TP
    t = time.time()
    s20 = Save(src20); sm = s20.read('game_db.dat'); E = C.Contenedor(entrada); dm = E.read('game_db.dat')
    Ls, Ld = X.LAY[7], X.LAY[8]
    sFN, sSN, sCN, _, _ = TP.tables(sm); dFN, dSN, dCN, _, _ = TP.tables(dm)
    pm = {}
    for a in open(pares_txt).read().split():
        v = [int(x) for x in a.split(':')]; pm[v[0]] = v[1]
    l20 = listas(sm, 7); l24 = listas(dm, 8)
    tr = U.traduccion(sm, dm)[0]
    ids = {persona(e, 7) - 1 for _, _, es in l20.values() for e in es if persona(e, 7)}
    resto = [i for i in ids if i not in pm]
    cab20 = PN.cabeceras(sm, resto)
    k20 = {i: PN.clave(sm, p, Ls, sFN, sSN, sCN) for i, p in cab20.items()}
    porn = PN.buscar(dm, {k for k in k20.values() if k}, Ld, dFN, dSN, dCN)
    print('personas de las relaciones: %d (jugadores convertidos %d, por nombre %d de %d) | %.0fs'
          % (len(ids), len(ids) - len(resto), sum(1 for k in k20.values() if k in porn), len(resto), time.time() - t))
    # fallback: same unique id, accepted only when FM24 has the same first name and surname for it
    uid20 = {i: struct.unpack_from('<I', sm, p + 4)[0] for i, p in cab20.items() if not (k20.get(i) and k20[i] in porn)}
    u24 = FP.por_uid(dm, set(uid20.values()))
    cab24 = PN.cabeceras(dm, set(u24.values()))
    k24 = {q: PN.clave(dm, p, Ld, dFN, dSN, dCN) for q, p in cab24.items()}
    porid = {}
    for i, u in uid20.items():
        q = u24.get(u)
        if q is None: continue
        a, b = k20.get(i), k24.get(q)
        if a is None or (b is not None and a[:2] == b[:2]): porid[i] = q
    print('  por id unico (mismo nombre): %d' % len(porid))
    # name-only people: type 5 records [pid][uid][uid][05][00 00 00 00][len][full name] (legends with no further
    # data, e.g. Jarque) and type 0x10 records [pid][uid][uid][10][00][first name id][surname id] (e.g. N'Kono)
    st20 = stubs(sm); st24 = stubs(dm)
    nom20 = {}
    for i in ids:
        if i in st20: nom20[i] = st20[i][1]
    for i, p in cab20.items():
        if i in nom20: continue
        if sm[p + 12] == 0x10:
            fn, sn = struct.unpack_from('<II', sm, p + 14); nom20[i] = (sFN.get(fn, '') + ' ' + sSN.get(sn, '')).strip()
        elif k20.get(i): nom20[i] = (k20[i][0] + ' ' + k20[i][1]).strip()
    por_nom24 = collections.defaultdict(list)
    for q, (pos, s) in st24.items(): por_nom24[s].append(q)
    def p24(i):
        if i in pm: return pm[i]
        k = k20.get(i)
        if k and k in porn: return porn[k]
        return porid.get(i)
    nombre_lista = {}   # FM24 person -> name, for the people already in the FM24 club lists
    usados24 = {persona(e, 8) - 1 for _, _, es in l24.values() for e in es if persona(e, 8)}
    cabu = PN.cabeceras(dm, usados24 - set(st24))
    for q, p in cabu.items():
        if dm[p + 12] == 0x10:
            fn, sn = struct.unpack_from('<II', dm, p + 14); nombre_lista[q] = (dFN.get(fn, '') + ' ' + dSN.get(sn, '')).strip()
        else:
            k = PN.clave(dm, p, Ld, dFN, dSN, dCN)
            if k: nombre_lista[q] = (k[0] + ' ' + k[1]).strip()
    for q in usados24 & set(st24): nombre_lista[q] = st24[q][1]
    asignados = set()
    def por_nombre(i, lista24):
        n = nom20.get(i)
        if not n: return None
        n = N.norm(n)
        loc = [q for q in lista24 if q in nombre_lista and N.norm(nombre_lista[q]) == n]
        if len(loc) == 1: return loc[0]
        cs = [q for q in por_nom24.get(nom20[i], []) if q not in asignados]
        if cs: return min(cs, key=lambda q: min([abs(q - a) for a in asignados] or [0]))
        return None
    edits = []; est = collections.Counter(); faltan = []; nuevas_de = {}
    for c20, (cp20, n20, es20) in l20.items():
        c24 = tr.get(c20, c20)
        if c24 is None or c24 not in l24: continue
        cp24, n24, es24 = l24[c24]
        nuevas = [e for e in es24 if not persona(e, 8)]; vistos = set()
        for e in es20:
            i = persona(e, 7)
            if not i: continue
            q = p24(i - 1)
            if q is None:
                q = por_nombre(i - 1, [persona(x, 8) - 1 for x in es24 if persona(x, 8)])
                if q is not None: est['por nombre (solo nombre)'] += 1
            if q is None and i - 1 in nom20: faltan.append((c24, e, nom20[i - 1])); continue
            if q is None: est['sin equivalente'] += 1; continue
            asignados.add(q)
            if q in vistos: continue
            vistos.add(q); nuevas.append(a_fm24(e, q + 1)); est['personas'] += 1
        nuevas_de[c24] = (cp24, n24, nuevas)
    # people FM24 does not have at all (e.g. Angel Morales): a name-only record of FM24 that no club list uses any
    # more is renamed and reused
    usados = {persona(e, 8) - 1 for _, _, ns in nuevas_de.values() for e in ns if persona(e, 8)}
    libres = sorted(q for q in usados24 & set(st24) if q not in usados and q not in asignados)
    for c24, e, nombre in faltan:
        cp24, n24, nuevas = nuevas_de[c24]
        if not libres: est['sin equivalente'] += 1; continue
        q = libres.pop(0); pos, viejo = st24[q]
        b = nombre.encode('utf-8'); ln = struct.unpack_from('<I', dm, pos)[0]
        edits.append((pos, 4 + ln, struct.pack('<I', len(b)) + b))
        nuevas.append(a_fm24(e, q + 1)); est['registro de solo nombre reutilizado'] += 1
        print('  %s -> registro %d (antes %s)' % (nombre, q, viejo))
    for c24, (cp24, n24, nuevas) in nuevas_de.items():
        nuevas = nuevas[:255]
        edits.append((cp24, 1 + 16 * n24, bytes([len(nuevas)]) + b''.join(nuevas))); est['clubes'] += 1
    edits.sort(); parts = []; cur = 0
    for p, ln, new in edits:
        if p < cur: est['solapadas'] += 1; continue
        parts.append(dm[cur:p]); parts.append(new); cur = p + ln
    parts.append(dm[cur:]); nm = b''.join(parts)
    E.escribir(salida, {('', 'game_db.dat'): nm})
    print('relaciones de clubes (leyendas, iconos, favoritos): ' + ' | '.join('%s %d' % kv for kv in est.items()) + ' | %.0fs' % (time.time() - t))
if __name__ == '__main__':
    a = sys.argv[1:]
    paso(a[0], a[1], a[2], a[3])
