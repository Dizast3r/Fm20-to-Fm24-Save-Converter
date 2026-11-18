#!/usr/bin/env python3
"""fm_trasplante.py - copia jugadores de una partida FM20 sobre jugadores de una partida base FM24 (EXPERIMENTAL).
Uso: fm_trasplante.py origen_fm20.fm base_fm24.fm salida.fm  id_origen:id_destino [id_origen:id_destino ...]
     (ids de jugador = columna id_jugador de los CSV de fm_export.py).  Nunca modifica origen ni base: escribe 'salida'."""
import sys, os, re, struct, shutil, subprocess, datetime
from fmsave import Save
import fm_export as X
import fm_contrato as K

def tables(m):
    tabs = []
    for nm in (b'David', b'Martin', b'Silva', b'Garcia', b'Smith', b'Peter', b'Juan', b'Lee'):
        for s in X.seed(m, nm, 0, len(m)):
            if any(a <= s < b for a, b, t in tabs): continue
            t = X.table(m, s)
            if len(t[2]) > 20000: tabs.append(t)
    tabs.sort()
    tabs = [t for t in tabs if not any(u is not t and u[0] <= t[0] and t[1] <= u[1] and (u[1] - u[0]) > (t[1] - t[0]) for u in tabs)]
    merged = []
    for a, b, t in tabs:
        if merged and a - merged[-1][1] < 256 and min(t) > max(merged[-1][2]): merged[-1][1] = b; merged[-1][2].update(t)
        else: merged.append([a, b, dict(t)])
    return merged[0][2], merged[1][2], (merged[2][2] if len(merged) > 2 else {}), max(b for a, b, t in merged), [(t[0], t[1]) for t in merged[:2]]

def players(m, L, FN, SN, CN, start, want):
    """localiza por id de jugador: devuelve {pid: dict(c, o, dpos, n)}"""
    out = {}
    for y in X.CUR.finditer(m, start):
        b = y.group(); c = y.start()
        if not (20 in b[:15] and 100 in (b[39], b[40])) or m[c + L['rep'] - 1] != 2: continue
        pid = struct.unpack_from('<I', m, c + L['pid'])[0]
        if pid not in want or pid in out: continue
        e = c + 69; key = struct.pack('<I', pid + 1); k = e; nm = None
        for _ in range(40):
            k = m.find(key, k + 1, e + 400000)
            if k < 0: break
            nm = X.find_name(m, k, L, FN, SN, CN, 260)
            if nm: break
        if nm:
            ks = []; q = e
            while True:
                q = m.find(key, q + 1, nm[0])
                if q < 0: break
                ks.append(q)
            out[pid] = dict(c=c, o=nm[0], dpos=nm[1], full=nm[2], n=nm[1] - nm[0] - L['slen'] - 4, ks=ks)
    return out

def fit(text, n):
    b = text.encode('utf8')
    while len(b) > n: text = text[:-1]; b = text.encode('utf8')
    return b + b' ' * (n - len(b))

import unicodedata
_TR = str.maketrans({'đ': 'd', 'Đ': 'D', 'ł': 'l', 'Ł': 'L', 'ø': 'o', 'Ø': 'O', 'ß': 'ss', 'ı': 'i', 'æ': 'ae', 'œ': 'oe'})
def norm(t):
    return ''.join(ch for ch in unicodedata.normalize('NFKD', t.translate(_TR)) if not unicodedata.combining(ch)).casefold().strip()
def lookup(text, rev, nrev):
    """id de 'text' en la tabla base: exacto, sin acentos, o por su primera palabra. Devuelve (id, como)"""
    if not text: return None, ''
    if text in rev: return rev[text], ''
    k = norm(text)
    if k in nrev: return nrev[k], 'sin acentos'
    first = k.split(' ')[0]
    if first != k and first in nrev: return nrev[first], 'abreviado'
    return None, 'no existe'

def squad_list(dm, person, limit, team=None):
    """lista de plantilla que contiene a 'person': [ff*4][n u16][n x id persona]. Devuelve (pos_contador, n)"""
    key = struct.pack('<I', person); q = -1
    while True:
        q = dm.find(key, q + 1, limit)
        if q < 0: return None
        for back in range(0, 200):
            L = q - 4 * back - 2
            if L < 8: break
            n = struct.unpack_from('<H', dm, L)[0]
            if back < n <= 250 and dm[L - 4:L] == b'\xff' * 4:
                ids = struct.unpack_from('<%dI' % n, dm, L + 2)
                if len(set(ids)) == n and all(0 < i < 3000000 for i in ids):
                    if team is not None:   # la ficha del equipo lleva [id de equipo - 1][uid][uid] poco antes de la lista
                        z = dm.find(struct.pack('<I', team - 1), max(0, L - 140), L)
                        if z < 0 or dm[z + 4:z + 8] != dm[z + 8:z + 12]: break
                    return L, n

def main():
    src, base, out = sys.argv[1:4]
    args = sys.argv[4:]
    if len(args) == 1 and args[0].startswith('@'): args = open(args[0][1:]).read().split()
    trip = [tuple(int(v) for v in a.split(':')) for a in args]
    move = {t[1]: t[2] for t in trip if len(t) == 3}
    loan = {t[1]: (t[2], t[3]) for t in trip if len(t) == 5}   # cesion: base -> (club de cesion, club dueno)
    pairs = [t[:2] for t in trip]
    ssv, bsv = Save(src), Save(base)
    Ls, Ld = X.LAY[ssv.version], X.LAY[bsv.version]
    sm = ssv.read('game_db.dat'); dm = bytearray(bsv.read('game_db.dat'))
    sFN, sSN, sCN, sstart, _ = tables(sm); dmb = bytes(dm); dFN, dSN, dCN, dstart, dpos = tables(dmb)
    addnames = os.environ.get('ANADIR_NOMBRES', '0') == '1'; pending = {0: [], 1: []}
    rFN = {}; rSN = {}
    for i, s in dFN.items(): rFN.setdefault(s, i)
    for i, s in dSN.items(): rSN.setdefault(s, i)
    rCN = {}; nFN = {}; nSN = {}; nCN = {}
    for i, t in dCN.items(): rCN.setdefault(t, i)
    for rv, nv in ((rFN, nFN), (rSN, nSN), (rCN, nCN)):
        for t, i in rv.items(): nv.setdefault(norm(t), i)
    sp = players(sm, Ls, sFN, sSN, sCN, sstart, {a for a, b in pairs})
    dp = players(dmb, Ld, dFN, dSN, dCN, dstart, {b for a, b in pairs}); del dmb
    shift = int(os.environ.get('DESPLAZAR_ANIOS', '-8'))
    member = {}
    for pid_d, D0 in dp.items():
        if pid_d not in move: member.setdefault(struct.unpack_from('<I', dm, D0['c'] + Ld['club'])[0], pid_d + 1)
    moved = [(d + 1, [struct.unpack_from('<I', dm, dp[d]['c'] + Ld['club'])[0]], [t]) for d, t in move.items() if d in dp]
    for d, (Lc, Oc) in loan.items():
        if d in dp and len(dp[d]['ks']) == 2:
            P0 = struct.unpack_from('<I', dm, dp[d]['ks'][0] + 4)[0]; L0 = struct.unpack_from('<I', dm, dp[d]['c'] + Ld['club'])[0]
            moved.append((d + 1, [P0, L0], [Oc, Lc]))
    import fm_cesiones as CS
    resize = os.environ.get('CAMBIAR_LONGITUD', '1') == '1'
    edits = []   # (posicion original, longitud original, bytes nuevos): se aplican todos juntos al final
    stats = dict(ok=0, sin_nombre=[], sin_contrato=0)
    for a, b in sorted(pairs, key=lambda ab: -dp[ab[1]]['c'] if ab[1] in dp else 0):
        if a not in sp or b not in dp: print('NO LOCALIZADO', a, b); continue
        notes = []
        S, D = sp[a], dp[b]
        fn = sFN.get(struct.unpack_from('<I', sm, S['o'])[0], ''); sn = sSN.get(struct.unpack_from('<I', sm, S['o'] + Ls['sn'])[0], '')
        D['hcn'] = struct.unpack_from('<I', dm, D['o'] + Ld['cn'])[0]
        hfn = dFN.get(struct.unpack_from('<I', dm, D['o'])[0], ''); hsn = dSN.get(struct.unpack_from('<I', dm, D['o'] + Ld['sn'])[0], '')
        if b in move:   # mover al jugador base a otro club: campo de club del bloque y de cada contrato
            struct.pack_into('<I', dm, D['c'] + Ld['club'], move[b])
            for kd in D['ks']: struct.pack_into('<I', dm, kd + 4, move[b])
        if b in loan and len(D['ks']) == 2:   # cesion: club actual = club de cesion; contrato 1 = dueno, contrato 2 = cesion
            Lc, Oc = loan[b]
            struct.pack_into('<I', dm, D['c'] + Ld['club'], Lc)
            struct.pack_into('<I', dm, D['ks'][0] + 4, Oc); struct.pack_into('<I', dm, D['ks'][1] + 4, Lc)
        # bloque de posiciones + atributos
        dm[D['c']:D['c'] + 69] = sm[S['c']:S['c'] + 69]
        # reputaciones, calidad, potencial y el byte que les sigue
        dm[D['c'] + Ld['rep']:D['c'] + Ld['rep'] + 6] = sm[S['c'] + Ls['rep']:S['c'] + Ls['rep'] + 6]
        dm[D['c'] + Ld['ca']:D['c'] + Ld['ca'] + 5] = sm[S['c'] + Ls['ca']:S['c'] + Ls['ca'] + 5]
        # peso y altura
        dm[D['c'] + 69 + Ld['wt']:D['c'] + 69 + Ld['wt'] + 4] = sm[S['c'] + 69 + Ls['wt']:S['c'] + 69 + Ls['wt'] + 4]
        # nombre y apellido (ids de las tablas de la partida base)
        sfn_id = struct.unpack_from('<I', sm, S['o'])[0]; ssn_id = struct.unpack_from('<I', sm, S['o'] + Ls['sn'])[0]; scn_id = struct.unpack_from('<I', sm, S['o'] + Ls['cn'])[0]
        did = {}
        for which, text, rev, nrev, tab, off in ((0, fn, rFN, nFN, dFN, 0), (1, sn, rSN, nSN, dSN, Ld['sn'])):
            idv, how = lookup(text, rev, nrev)
            if idv is None and addnames and text:
                idv = rev[text] = len(tab) + len(pending[which]); pending[which].append(text); how = 'nombre anadido'
            if idv is not None: struct.pack_into('<I', dm, D['o'] + off, idv); did[which] = idv
            if how: notes.append(f'"{text}": {how}')
        # tercer identificador: nombre con el que el juego muestra al jugador
        shown = sn; dcn = 0xffffffff
        if scn_id != 0xffffffff:
            if scn_id == sfn_id and 0 in did: dcn = did[0]; shown = fn
            elif scn_id == ssn_id and 1 in did: dcn = did[1]
            else:
                ctext = sCN.get(scn_id, ''); idv, how = lookup(ctext, rCN, nCN)
                if idv is not None: dcn = idv; shown = ctext
                elif ctext: notes.append(f'apodo "{ctext}": no existe')
        struct.pack_into('<I', dm, D['o'] + Ld['cn'], dcn)
        # nacimiento (desplazado) y nacion
        d, y = struct.unpack_from('<HH', sm, S['dpos']); d &= 0x1ff; y += shift
        if d == 366 and not (y % 4 == 0 and (y % 100 or y % 400 == 0)): d = 365
        struct.pack_into('<HH', dm, D['dpos'], d, y)
        dm[D['dpos'] + 9:D['dpos'] + 13] = sm[S['dpos'] + 9:S['dpos'] + 13]
        # personalidad (8 rasgos ocultos 1-20)
        dm[D['dpos'] + Ld['pers']:D['dpos'] + Ld['pers'] + 8] = sm[S['dpos'] + Ls['pers']:S['dpos'] + Ls['pers'] + 8]
        born = X.date(dm, D['dpos'])
        # --- contrato: sueldo, fechas (desplazadas) y primas/clausulas ---
        def putdate(dst, src):
            d, y = struct.unpack_from('<HH', sm, src)
            if y > 1900:
                y += shift
                if (d & 0x1ff) == 366 and not (y % 4 == 0 and (y % 100 or y % 400 == 0)): d -= 1
            struct.pack_into('<HH', dm, dst, d, y)
        clause_edits = []
        es_cesion = b in loan and len(D['ks']) == 2 and len(S['ks']) >= 2
        if es_cesion:
            cur20 = struct.unpack_from('<I', sm, S['c'] + Ls['club'])[0]
            kl = [k for k in S['ks'][1:] if struct.unpack_from('<I', sm, k + 4)[0] == cur20]
            kl = kl[-1] if kl else S['ks'][-1]
            fs = K.fields(sm, S['ks'][0], ssv.version)
            struct.pack_into('<I', dm, D['ks'][1] + Ld['wage'], struct.unpack_from('<I', sm, kl + Ls['wage'])[0])
            l20 = CS.loan_dates(sm, kl); l24 = CS.loan_dates(dm, D['ks'][1])
            if l20 and l24:
                putdate(l24[0], l20[0]); putdate(l24[1], l20[1]); notes.append('cesion: fechas copiadas')
                # loan options (same bit field in FM20 and FM24): 0x0002/0x0004 recall + cup games, 0x0001 can play
                # against its own club, 0x1000 cannot be terminated, 0x8000 can play against the parent club's B team
                o20 = l20[0] - (67 if ssv.version == 7 else 88); o24 = l24[0] - (88 if bsv.version == 8 else 67)
                dm[o24:o24 + 2] = sm[o20:o20 + 2]
            else: notes.append('cesion: fechas no localizadas')
            dest_ks = [D['ks'][0]]; src_k = S['ks'][0]
        else:
            fs = None; src_k = None
            for k_ in reversed(S['ks']):   # el ultimo contrato legible (los de cesion/filial tienen otra estructura)
                fs = K.fields(sm, k_, ssv.version)
                if fs: src_k = k_; break
            dest_ks = D['ks']
        if fs:
            wage = struct.unpack_from('<I', sm, src_k + Ls['wage'])[0]
            ents = [bytes(sm[fs['count'] + 1 + 8 * i:fs['count'] + 9 + 8 * i]) for i in range(fs['n'])]
            ents = [x for x in ents if struct.unpack_from('<H', x, 6)[0] in (0x00, 0x20, 0x21, 0x22, 0x23, 0x26)]
            putdate(D['c'] + 69 + Ld['joined'], fs['date2'])
            nrec = 0
            for kd in dest_ks:
                struct.pack_into('<I', dm, kd + Ld['wage'], wage)
                fd = K.fields(dm, kd, bsv.version)
                if not fd: continue
                nrec += 1
                putdate(fd['start'], fs['start']); putdate(fd['end'], fs['end']); putdate(fd['date2'], fs['date2'])
                clause_edits.append((fd['count'], fd['n'], bytes([len(ents)]) + b''.join(ents)))
            notes.append(f'contrato: sueldo {wage} GBP/sem, fin {X.date(sm, fs["end"])[:4]}{shift:+d}, {len(ents)} primas, {nrec}/{len(D["ks"])} registros')
        else: notes.append('contrato de origen no localizado')
        # --- cambios que alteran la longitud (de mayor a menor posicion) ---
        if D['n']:   # nombre completo escrito como texto
            full = f'{fn} {sn}'.encode('utf8') if resize else fit(f'{fn} {sn}', D['n'])
            p = D['o'] + Ld['slen']
            if resize: edits.append((p, 4 + D['n'], struct.pack('<I', len(full)) + full, 'nombre_completo'))
            else: dm[p:p + 4 + D['n']] = struct.pack('<I', len(full)) + full
        if resize:
            for cp, n_old, new in sorted(clause_edits, reverse=True):
                edits.append((cp, 1 + 8 * n_old, new, 'primas'))
        if resize:   # nombre de la camiseta: cadena con el nombre del sustituido dentro de su bloque de jugador
            hcn = dCN.get(D['hcn'], '')
            cands = {t for t in (hsn, hcn, hfn, f'{hfn} {hsn}', f'{hfn[:1]}. {hsn}', f'{hfn[:1]}.{hsn}', hsn.split(' ')[0]) if t}
            new = shown.encode('utf8'); done = False
            for t in sorted(cands, key=len, reverse=True):
                pat = struct.pack('<I', len(t.encode('utf8'))) + t.encode('utf8')
                p = dm.find(pat, D['c'] + 69, D['c'] + 900)
                if p >= 0 and p < D['o']:
                    edits.append((p, len(pat), struct.pack('<I', len(new)) + new, 'camiseta')); notes.append(f'camiseta "{t}" cambiada'); done = True; break
        ca, pa = struct.unpack_from('<HH', sm, S['c'] + Ls['ca'])
        stats['ok'] += 1
        if es_cesion: stats['cesiones'] = stats.get('cesiones', 0) + 1
        for nt in notes:
            if 'no existe' in nt: stats['sin_nombre'].append(nt)
            if 'sin acentos' in nt or 'abreviado' in nt: stats.setdefault('aprox', []).append(nt)
            if 'anadido' in nt: stats['anadidos'] = stats.get('anadidos', 0) + 1
            if 'no localizado' in nt: stats['sin_contrato'] += 1
        if os.environ.get('VERBOSO'): print(f'{fn} {sn} (CA {ca}/{pa}, nac. {born})  ->  sustituye a {hfn} {hsn}', '| ' + '; '.join(notes) if notes else '')
    print('cesiones trasplantadas:', stats.get('cesiones', 0))
    print('nombres aproximados:', len(stats.get('aprox', [])), stats.get('aprox', [])[:30])
    print('trasplantados', stats['ok'], '| contrato de origen no localizado', stats['sin_contrato'], '| nombres que no existen en la base', len(stats['sin_nombre']), stats['sin_nombre'][:40])
    # nombres nuevos: se anaden al final de su tabla (primero la de apellidos, que esta mas atras) y se actualiza el contador
    for which in (1, 0):
        if not pending[which]: continue
        ta, tb = dpos[which]; tab = (dFN, dSN)[which]; base_n = len(tab)
        assert struct.unpack_from('<I', dm, ta - 4)[0] == base_n
        blob = b''.join(struct.pack('<II', base_n + i, len(t.encode('utf8'))) + t.encode('utf8') for i, t in enumerate(pending[which]))
        edits.append((tb, 0, blob, 'tabla_nombres')); struct.pack_into('<I', dm, ta - 4, base_n + len(pending[which]))
        print('tabla', ('nombres', 'apellidos')[which], ': anadidas', len(pending[which]), 'entradas', pending[which][:12])
    # economia: saldo (i32) y lista de patrocinios de cada club, emparejando clubes por su id unico
    if os.environ.get('ECONOMIA') == '1':
        import fm_patrocinios as PT, fm_ligas as LG, fm_clubes as CB
        c20 = PT.by_club20(sm, LG.team_zone(sm)); dmb = bytes(dm); c24 = PT.by_club24(dmb, CB.clubs(dmb, 8, 60 << 20)); del dmb
        def shiftd(buf, p):
            d, y = struct.unpack_from('<HH', buf, p)
            if y < 1950: return
            y += shift; dd = d & 0x1ff
            if dd == 366 and not (y % 4 == 0 and (y % 100 or y % 400 == 0)): dd = 365
            struct.pack_into('<HH', buf, p, (d & ~0x1ff) | dd, y)
        nsal = nsp = 0
        for u, z in c24.items():
            a2 = c20.get(u)
            if not a2: continue
            dm[z['bal']:z['bal'] + 4] = sm[a2['bal']:a2['bal'] + 4]; nsal += 1
            if z['n'] == 0 or os.environ.get('PATROCINIOS', '1') != '1': continue
            sids = [bytes(dm[z['cnt'] + 1 + 24 * i + 15:z['cnt'] + 1 + 24 * i + 19]) for i in range(z['n'])]
            recs = []
            for i in range(a2['n']):
                r = bytearray(sm[a2['cnt'] + 1 + 24 * i:a2['cnt'] + 25 + 24 * i])
                shiftd(r, 2); shiftd(r, 6); r[15:19] = sids[i % len(sids)]; recs.append(bytes(r))
            edits.append((z['cnt'], 1 + 24 * z['n'], bytes([len(recs)]) + b''.join(recs), 'patrocinios')); nsp += 1
        print('economia: saldo copiado en', nsal, 'clubes | patrocinios reemplazados en', nsp)
    # listas de plantilla de los equipos: quitar a los reciclados de su equipo anterior y anadirlos al nuevo
    if moved and os.environ.get('LISTAS', '1') == '1':
        import fm_ligas as LG, fm_plantillas as PL
        teams = LG.team_zone(bytes(dm)); rem = {}; add = {}; fail = 0
        falta = {t for _, olds, news in moved for t in olds + news if t not in teams}
        if falta:   # equipos fuera de la zona habitual: buscar su ficha en todo el fichero
            import fm_equipos as EQ
            for t, v in EQ.teams(bytes(dm), 0, len(dm)).items():
                if t in falta and t not in teams: teams[t] = v
            print('fichas de equipo buscadas fuera de la zona habitual:', len(falta), '| encontradas:', len(falta & set(teams)))
        for person, olds, news in moved:
            if any(t not in teams for t in olds + news): fail += 1; continue
            for t in olds:
                if t not in news: rem.setdefault(t, set()).add(person)
            for t in news:
                if t not in olds: add.setdefault(t, []).append(person)
        nl = 0; byq = {}
        for t in set(rem) | set(add):
            r = PL.squad_of(dm, teams[t])
            if not r: fail += 1; continue
            g = byq.setdefault(r[0], [r[1], r[2], set(), []]); g[2] |= rem.get(t, set()); g[3] += add.get(t, [])
        for q, (n, ids0, rm, ad) in byq.items():
            ids = [i for i in ids0 if i not in rm]; ids += [i for i in dict.fromkeys(ad) if i not in ids]
            edits.append((q, 2 + 4 * n, struct.pack('<H', len(ids)) + struct.pack('<%dI' % len(ids), *ids), 'plantilla')); nl += 1
        print('listas de plantilla modificadas:', nl, '| fallos:', fail)
    # aplicar todos los cambios de longitud en una sola pasada
    edits.sort(key=lambda e: (e[0], e[1])); parts = []; cur = 0; skipped = 0; prev = None; why = {}
    for p, ln, new, tag in edits:
        if p < cur: skipped += 1; k = (prev, tag); why[k] = why.get(k, 0) + 1; continue
        prev = tag
        parts.append(bytes(dm[cur:p])); parts.append(new); cur = p + ln
    parts.append(bytes(dm[cur:])); dm = bytearray(b''.join(parts)); del parts
    print('cambios de longitud aplicados:', len(edits) - skipped, '| descartados por solaparse:', skipped, why)
    # reempaquetar: misma longitud comprimida que el original, rellenando con un bloque ignorable
    g = [e for e in bsv.entries if e['name'] == 'game_db.dat'][0]
    for lvl in ('-9', '-15', '-19'):
        z = subprocess.run(['zstd', '-T0', lvl, '-c', '-q'], input=bytes(dm), stdout=subprocess.PIPE, check=True).stdout
        if len(z) <= g['comp'] - 8: break
    else: sys.exit(f'no cabe: {len(z)} > {g["comp"]} (hace falta reescribir el indice)')
    shutil.copyfile(base, out)
    with open(out, 'r+b') as o:
        o.seek(26 + g['off']); o.write(z); pad = g['comp'] - len(z)
        o.write(b'\x50\x2a\x4d\x18' + struct.pack('<I', pad - 8) + bytes(pad - 8))
    if len(dm) != g['raw']:   # la base de datos cambio de tamano: actualizar su longitud en el indice
        from fmsave import _unz
        toc = bytearray(_unz(bsv.m[bsv.toc_off + 9:], bsv.comp)); p = 0
        n = struct.unpack_from('<I', toc, p)[0]; p += 4 + n; cnt = struct.unpack_from('<I', toc, p)[0]; p += 4
        for _ in range(cnt):
            n = struct.unpack_from('<I', toc, p)[0]; nm = bytes(toc[p + 4:p + 4 + n]); p += 4 + n
            n = struct.unpack_from('<I', toc, p)[0]; p += 4 + n
            if nm == b'game_db':
                assert struct.unpack_from('<Q', toc, p + 16)[0] == g['raw']; struct.pack_into('<Q', toc, p + 16, len(dm)); break
            p += 40
        zt = subprocess.run(['zstd', '-19', '-c', '-q'], input=bytes(toc), stdout=subprocess.PIPE, check=True).stdout
        with open(out, 'r+b') as o:
            o.seek(bsv.toc_off + 9); o.write(zt); o.truncate()
        print('indice actualizado: game_db', g['raw'], '->', len(dm), 'bytes')
    chk = Save(out).read('game_db.dat')
    print('escrito', out, '| nivel zstd', lvl, '| relleno', pad, '| verificacion de lectura:', chk == bytes(dm))

if __name__ == '__main__':
    main()
