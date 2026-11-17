#!/usr/bin/env python3
"""fm_ligas.py - intercambia de division parejas de clubes en una partida base de FM24 para igualar la Primera de una partida FM20 (EXPERIMENTAL).
Uso: fm_ligas.py origen_fm20.fm base_fm24.fm salida.fm"""
import sys, os, re, struct, shutil, subprocess, json
from fmsave import Save, _unz
import fm_equipos as E

def subdirs(sv):
    r = sv.toc_rest; q = 4; out = {}
    def s():
        nonlocal q
        n = struct.unpack_from('<I', r, q)[0]; q += 4; v = r[q:q + n].decode('utf8', 'replace'); q += n; return v
    for _ in range(struct.unpack_from('<I', r, 0)[0]):
        s(); cnt = struct.unpack_from('<I', r, q)[0]; q += 4
        for _ in range(cnt):
            n = s(); e = s(); off, c, raw, t1, t2 = struct.unpack_from('<QQQqq', r, q); q += 40
            out[n + e] = dict(name=n + e, off=off, comp=c, raw=raw)
    return out

def team_zone(m):
    z = m.find(struct.pack('<II', 1724, 1724) + b'\x0a\x00')      # ficha de equipo del Espanyol (id unico 1724)
    return E.teams(m, max(0, z - (60 << 20)), min(len(m), z + (60 << 20)))

def table_rows(d, ids, n):
    """posicion de la tabla de clasificacion: n filas de 414 bytes que empiezan por un id de equipo de la division"""
    for p in range(0, len(d) - 414 * n):
        if struct.unpack_from('<I', d, p)[0] in ids and all(struct.unpack_from('<I', d, p + 414 * i)[0] in ids for i in range(n)): return p
    return None

def swap_all_tables(c, ids, sw, n):
    """todas las tablas del fichero de competicion: n filas de tamano fijo que empiezan por un id de equipo de la division.
    Cambia los ids segun sw; si la tabla estaba ordenada por id, la vuelve a ordenar. Devuelve [(inicio, tamano_fila)]"""
    import collections
    pos = [i for i in range(len(c) - 4) if struct.unpack_from('<I', c, i)[0] in ids]
    gaps = collections.Counter(b - a for a, b in zip(pos, pos[1:]) if 60 <= b - a <= 4000)
    done = []
    for S, cnt in gaps.most_common(6):
        if cnt < n - 3: continue
        for p in pos:
            if p + S * n > len(c) or any(st <= p < st + sz * n for st, sz in done): continue
            row_ids = [struct.unpack_from('<I', c, p + S * i)[0] for i in range(n)]
            if not all(t in ids for t in row_ids) or len(set(row_ids)) != n: continue
            was_sorted = row_ids == sorted(row_ids)
            rows = [bytearray(c[p + S * i:p + S * (i + 1)]) for i in range(n)]
            for r in rows:
                t = struct.unpack_from('<I', r, 0)[0]
                if t in sw: struct.pack_into('<I', r, 0, sw[t])
            if was_sorted: rows.sort(key=lambda r: struct.unpack_from('<I', r, 0)[0])
            c[p:p + S * n] = b''.join(rows); done.append((p, S))
    return done

FIX = re.compile(rb'\x02\x00\x00(.{4})\xff\x00\x00(.{4})\xff\x00', re.S)

def main(src, base, out):
    ssv, bsv = Save(src), Save(base); sub = subdirs(bsv); allent = {e['name']: e for e in bsv.entries}; allent.update(sub)
    def rd(name): e = allent[name]; return bytearray(_unz(bsv.m[26 + e['off']:26 + e['off'] + e['comp']], bsv.comp))
    sm = ssv.read('game_db.dat'); dm = rd('game_db.dat')
    ts = team_zone(sm); tb = team_zone(bytes(dm))
    s1 = {v['uid'] for v in ts.values() if v['div'] == 51}
    b1 = {v['uid']: t for t, v in tb.items() if v['div'] == 51}; b2 = {v['uid']: t for t, v in tb.items() if v['div'] == 52}
    up = sorted(b2[u] for u in s1 if u in b2); down = sorted(t for u, t in b1.items() if u not in s1)
    missing = [u for u in s1 if u not in b1 and u not in b2]
    pairs = list(zip(up, down))
    print('Primera FM20:', len(s1), '| ya en Primera en la base:', len([u for u in s1 if u in b1]), '| suben:', up, '| bajan:', down, '| sin sitio (no estan en Primera ni Segunda de la base):', missing)
    new = {}
    # 1) fichas de equipo: intercambiar division actual y anterior
    for a, b in pairs:
        pa, pb = tb[a]['divpos'], tb[b]['divpos']; xa, xb = bytes(dm[pa:pa + 8]), bytes(dm[pb:pb + 8]); dm[pa:pa + 8] = xb; dm[pb:pb + 8] = xa
    # reputacion del equipo: solo equipos verificados (id de club real en ambas partidas, valores en rango); el puesto NO se copia
    import csv
    # equipo real = equipo con jugadores en la partida (CSV de fm_export.py)
    real20 = {int(x['id_club']) for x in csv.DictReader(open(os.environ.get('CSV20', 'fm20_jugadores.csv'), encoding='utf-8-sig')) if x['id_club']}
    real24 = {int(x['id_club']) for x in csv.DictReader(open(os.environ.get('CSV24', 'n24_jugadores.csv'), encoding='utf-8-sig')) if x['id_club']}
    su = {}
    for t, v in ts.items():
        if t in real20: su.setdefault(v['uid'], v)
    nrep = 0; seen = set()
    for t, v in sorted(tb.items()):
        if t not in real24 or v['uid'] in seen: continue
        o = su.get(v['uid'])
        if not o: continue
        r24 = struct.unpack_from('<H', dm, v['pos'] + 15)[0]; r20 = struct.unpack_from('<H', sm, o['pos'] + 15)[0]
        if not (0 < r24 <= 10000 and 0 < r20 <= 10000): continue
        struct.pack_into('<H', dm, v['pos'] + 15, r20); nrep += 1; seen.add(v['uid'])
    print('equipos con reputacion copiada:', nrep, '| fichas de equipo descartadas por dudosas:', len(tb) - nrep)
    # cesiones de FM24 en los clubes convertidos: adelantar su fin al dia siguiente al inicio, para que el juego las termine
    ef = os.environ.get('CESIONES_EQUIPOS')
    if ef:
        import csv, fm_cesiones as CS
        targets = {int(t) for t in open(ef).read().split()}
        nend = 0
        for x in csv.DictReader(open(os.environ.get('CSV24', 'n24_jugadores.csv'), encoding='utf-8-sig')):
            if not x['id_club'] or int(x['id_club']) not in targets: continue
            c = int(x['pos_bloque']); o = int(x['pos_nombre']); key = struct.pack('<I', int(x['id_jugador']) + 1); kk = []; q = c
            while True:
                q = dm.find(key, q + 1, o)
                if q < 0: break
                kk.append(q)
            if len(kk) < 2 or dm[kk[0] + 18:kk[0] + 20] != b'\x00\x01': continue
            if struct.unpack_from('<I', dm, kk[-1] + 4)[0] != int(x['id_club']): continue
            r = CS.loan_dates(dm, kk[-1])
            if not r: continue
            d0, y0 = struct.unpack_from('<HH', dm, r[1])          # inicio de la cesion (o fecha de inicio de la partida)
            d, y = struct.unpack_from('<HH', dm, r[0])
            nd, ny = (d0 & 0x1ff) + 1, y0
            if nd > 365: nd, ny = 1, y0 + 1
            struct.pack_into('<HH', dm, r[0], (d & ~0x1ff) | nd, ny); nend += 1
        print('cesiones de FM24 que terminan al dia siguiente:', nend)
    # saldo del club (prueba: solo el club indicado). FM20: 42 ff [i8] 01006c07 x3 ; FM24: 42 ff 00 [i8] 01006c07 x3
    if os.environ.get('SALDO_CLUB'):
        n20, n24 = os.environ['SALDO_CLUB'].split('|')
        tail = b'\x01\x00\x6c\x07' * 3
        p20 = sm.find(struct.pack('<I', len(n20.encode())) + n20.encode() + struct.pack('<I', len(n20.encode())) + n20.encode())
        p24 = bytes(dm).find(struct.pack('<I', len(n24.encode())) + n24.encode())
        q20 = re.compile(rb'\x42\xff(.{8})' + re.escape(tail), re.S); q24 = re.compile(rb'\x42\xff\x00(.{8})' + re.escape(tail), re.S)
        a20 = [x for x in q20.finditer(sm, max(0, p20 - 600), p20)]
        a24 = q24.search(bytes(dm), p24, p24 + 3000)
        if a20 and a24:
            v = struct.unpack('<q', a20[-1].group(1))[0]; old = struct.unpack_from('<q', dm, a24.start(1))[0]
            struct.pack_into('<q', dm, a24.start(1), v); print('saldo', n24, ':', old, '->', v, 'GBP')
        else: print('saldo: no localizado', bool(a20), bool(a24))
    # presupuestos de fichajes (original y actual) y salarial semanal, en GBP; solo clubes cuya lectura en FM20 es coherente
    if os.environ.get('PRESUPUESTOS') == '1':
        import csv, collections, fm_economia as EC
        tz20 = team_zone(sm); sal = collections.Counter()
        for x in csv.DictReader(open(os.environ.get('CSV20', 'fm20_jugadores.csv'), encoding='utf-8-sig')):
            if x['id_club'] and x['sueldo_semanal_GBP'] and int(x['id_club']) in tz20: sal[tz20[int(x['id_club'])]['uid']] += int(x['sueldo_semanal_GBP'])
        b20 = EC.budgets_all(sm, 7); b24 = EC.budgets_all(bytes(dm), 8); nb = 0
        for u, g24 in b24.items():
            g20 = b20.get(u)
            if not g20 or sal[u] <= 0: continue
            w20 = struct.unpack_from('<i', sm, g20['wage'])[0]
            if not 0.5 <= w20 / sal[u] <= 8: continue
            for k in ('orig', 'cur', 'wage'): dm[g24[k]:g24[k] + 4] = sm[g20[k]:g20[k] + 4]
            nb += 1
        print('clubes con presupuestos copiados:', nb)
    new['game_db.dat'] = dm
    # 2) tablas de clasificacion
    c1, c2 = rd('comp_67.dat'), rd('comp_68.dat'); i1, i2 = set(b1.values()), set(b2.values())
    up2down = dict(pairs); down2up = {b: a for a, b in pairs}
    t1 = swap_all_tables(c1, i1, down2up, len(i1)); t2 = swap_all_tables(c2, i2, up2down, len(i2))
    print('tablas en Primera (inicio, tamano de fila):', t1, '| en Segunda:', t2)
    # lista de participantes al final del fichero (despues de la ultima tabla)
    nlist = 0
    for a, b in pairs:
        p = bytes(c1).rfind(struct.pack('<I', b))
        if p > max(st + sz * len(i1) for st, sz in t1): struct.pack_into('<I', c1, p, a); nlist += 1
        p = bytes(c2).rfind(struct.pack('<I', a))
        if p > max(st + sz * len(i2) for st, sz in t2): struct.pack_into('<I', c2, p, b); nlist += 1
    print('entradas cambiadas en las listas de participantes:', nlist)
    new['comp_67.dat'] = c1; new['comp_68.dat'] = c2
    # 3) calendario: intercambiar los dos clubes en todos los partidos
    fx = rd('fix_man.dat'); sw = {}
    for a, b in pairs: sw[a] = b; sw[b] = a
    nfix = 0
    for x in FIX.finditer(bytes(fx)):
        for g in (1, 2):
            t = struct.unpack('<I', x.group(g))[0]
            if t in sw: struct.pack_into('<I', fx, x.start(g), sw[t]); nfix += 1
    new['fix_man.dat'] = fx
    print('parejas intercambiadas:', len(pairs), '| apariciones cambiadas en el calendario:', nfix)
    # escribir: cada fichero vuelve a su hueco, rellenando con un bloque ignorable
    shutil.copyfile(base, out)
    with open(out, 'r+b') as o:
        for name, data in new.items():
            e = allent[name]; assert len(data) == e['raw']
            for lvl in ('-9', '-15', '-19', '-22'):
                z = subprocess.run(['zstd', '-T0', '--ultra', lvl, '-c', '-q'], input=bytes(data), stdout=subprocess.PIPE, check=True).stdout
                if len(z) <= e['comp'] - 8 or len(z) == e['comp']: break
            else: sys.exit(f'{name}: no cabe ({len(z)} > {e["comp"]})')
            o.seek(26 + e['off']); o.write(z); pad = e['comp'] - len(z)
            if pad: o.write(b'\x50\x2a\x4d\x18' + struct.pack('<I', pad - 8) + bytes(pad - 8))
            print(' ', name, 'nivel', lvl, 'relleno', pad)
    chk = Save(out); sb = subdirs(chk)
    ok = all(_unz(chk.m[26 + allent[n]['off']:26 + allent[n]['off'] + allent[n]['comp']], chk.comp) == bytes(d) for n, d in new.items())
    print('escrito', out, '| verificacion de lectura:', ok)
    json.dump(dict(pairs=pairs), open('ligas_pares.json', 'w'))

if __name__ == '__main__':
    main(*sys.argv[1:4])
