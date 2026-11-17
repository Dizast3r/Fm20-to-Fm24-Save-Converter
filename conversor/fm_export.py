#!/usr/bin/env python3
"""fm_export.py - exporta a CSV todos los jugadores de una partida de FM20 o FM24 (solo lectura; EXPERIMENTAL).
Uso: fm_export.py partida.fm salida.csv"""
import sys, re, struct, datetime, csv
from fmsave import Save

ATTRS = ['Centros','Regate','Remate','Cabeceo','Tiros lejanos','Marcaje','Desmarques','Pases','Penaltis','Entradas','Vision',
 'PO Blocaje','PO Juego aereo','PO Mando area','PO Comunicacion','PO Saques puerta','PO Saques mano',
 'Anticipacion','Decisiones','PO Uno contra uno','Colocacion','PO Reflejos','Control','Tecnica','Pie izquierdo','Pie derecho',
 'Talento','Corners','Juego en equipo','Sacrificio','Saques de banda','PO Excentricidad','PO Salidas','PO Tendencia despejar',
 'Aceleracion','Tiros libres','Fuerza','Resistencia','Velocidad','Salto','Liderazgo','Juego sucio','Equilibrio','Valentia',
 'Consistencia','Agresividad','Agilidad','Partidos importantes','Propension lesiones','Polivalencia','Recuperacion fisica',
 'Determinacion','Serenidad','Concentracion']
POS = ['POR','LIB','DFI','DFC','DFD','MCD','MI','MC','MD','MPI','MP','MPD','DL','CRI','CRD']

def date(m, p):
    d, y = struct.unpack_from('<HH', m, p); d &= 0x1ff
    if not (1900 < y < 2100 and 1 <= d <= 366): return ''
    return (datetime.date(y, 1, 1) + datetime.timedelta(days=d - 1)).isoformat()

def entry(m, p):
    i, n = struct.unpack_from('<II', m, p)
    if not 0 <= n < 80: return None
    try: s = m[p + 8:p + 8 + n].decode('utf8')
    except UnicodeDecodeError: return None
    if any(ord(c) < 32 for c in s): return None
    return i, s, p + 8 + n

def table(m, seed):
    """recorre hacia delante y hacia atras una tabla [id u32][len u32][texto] con ids consecutivos"""
    d = {}; p = seed
    while True:
        e = entry(m, p)
        if not e or (d and e[0] != last + 1): break
        d[e[0]] = e[1]; last = e[0]; p = e[2]
    end = p
    p = seed; cur = struct.unpack_from('<I', m, p)[0]
    while True:
        if cur == 0: break
        want = struct.pack("<I", cur - 1); q = m.rfind(want, max(0, p - 96), p); ok = False
        while q >= 0:
            e = entry(m, q)
            if e and e[2] == p: d[e[0]] = e[1]; p = q; cur -= 1; ok = True; break
            q = m.rfind(want, p - 96, q)
        if not ok:
            # intenta saltar una entrada ilegible: busca la entrada cur-2 un poco mas atras
            want = struct.pack('<I', cur - 2) if cur >= 2 else None; q = m.rfind(want, max(0, p - 400), p) if want else -1; ok2 = False
            while q >= 0:
                e = entry(m, q)
                if e and e[2] <= p and p - e[2] < 200: d[e[0]] = e[1]; p = q; cur -= 2; ok2 = True; break
                q = m.rfind(want, max(0, p - 400), q)
            if not ok2: break
    return p, end, d

def seed(m, name, lo, hi):
    return [x.start() - 4 for x in re.finditer(re.escape(struct.pack('<I', len(name)) + name), m) if x.start() >= 4]

LAY = {7: dict(wage=8, pid=-38, rep=-25, ca=-19, club=-4, joined=5, sharp=9, cond=13, wt=21, name=re.compile(rb'\x00\x00\x00\x00..[\x94-\xf5]\x07\xff', re.S), nback=12, sn=4, cn=8, slen=12, pers=13),
       8: dict(wage=12, pid=-42, rep=-29, ca=-23, club=-8, joined=9, sharp=13, cond=17, wt=28, name=re.compile(rb'\x00\x00\x00\x00\x00..[\x94-\xf5]\x07\xff', re.S), nback=14, sn=5, cn=10, slen=15, pers=17)}
def find_name(m, k, L, FN, SN, CN, span=700):
    """busca tras el contrato la ficha de nombre validando todos sus campos; devuelve (pos, pos_fecha, nombre_completo)"""
    F = 0xffffffff
    for p in range(k + 12, k + span):
        fn = struct.unpack_from('<I', m, p)[0]
        if fn != F and fn not in FN: continue
        sn = struct.unpack_from('<I', m, p + L['sn'])[0]
        if sn != F and sn not in SN: continue
        cn = struct.unpack_from('<I', m, p + L['cn'])[0]
        n = struct.unpack_from('<I', m, p + L['slen'])[0]
        if n > 80 or (fn == sn == cn == F and n == 0): continue
        d = p + L['slen'] + 4 + n
        if not date(m, d): continue
        y = struct.unpack_from('<H', m, d + 2)[0]
        if not 1930 <= y <= 2035: continue
        if struct.unpack_from('<I', m, d + 9)[0] > 5000: continue
        if not all(1 <= c <= 20 for c in m[d + L['pers']:d + L['pers'] + 8]): continue
        try: full = m[p + L['slen'] + 4:d].decode('utf8')
        except UnicodeDecodeError: continue
        if any(ord(ch) < 32 for ch in full): continue
        return p, d, full
    return None

CUR = re.compile(rb'[\x01-\x14]{15}[\x01-\x64]{54}', re.S)
NAME = re.compile(rb'\x00\x00\x00\x00..[\x94-\xf5]\x07\xff...\xff', re.S)

def main(path, out):
    sv = Save(path); L = LAY[sv.version]; m = sv.read('game_db.dat')
    A = 0; B = len(m)
    # tablas de nombres: se localizan a partir de entradas muy comunes
    tabs = []
    for nm in (b'David', b'Martin', b'Silva', b'Garcia', b'Smith', b'Peter', b'Juan', b'Lee'):
        for s in seed(m, nm, A, B):
            s += A
            i = struct.unpack_from('<I', m, s)[0]
            if any(a <= s < b for a, b, t in tabs): continue
            t = table(m, s)
            if len(t[2]) > 20000: tabs.append(t)
    tabs.sort()
    tabs = [t for t in tabs if not any(u is not t and u[0] <= t[0] and t[1] <= u[1] and (u[1] - u[0]) > (t[1] - t[0]) for u in tabs)]
    merged = []
    for a, b, t in tabs:   # une tablas contiguas (una entrada ilegible parte la tabla en dos)
        if merged and a - merged[-1][1] < 256 and min(t) > max(merged[-1][2]): merged[-1][1] = b; merged[-1][2].update(t)
        else: merged.append([a, b, dict(t)])
    tabs = merged
    print('tablas de nombres (inicio, fin, entradas, id min, id max):', [(a, b, len(t), min(t), max(t)) for a, b, t in tabs], file=sys.stderr)
    FN, SN, CN = tabs[0][2], tabs[1][2], (tabs[2][2] if len(tabs) > 2 else {})
    rows = 0; multi = 0; prev = max(b for a, b, t in tabs)
    w = csv.writer(open(out, 'w', newline='', encoding='utf-8-sig'))
    w.writerow(['id_jugador','nombre','apellido','apodo','nombre_completo','id_nombre','id_apellido','nacimiento','id_nacion','id_club','CA','PA','rep1','rep2','rep3',
                'altura_cm','peso_kg','forma_fisica','ritmo','fecha_club','sueldo_semanal_GBP','id_club_contrato'] + POS + ATTRS + ['pos_bloque', 'pos_nombre'])
    start = prev; nolink = 0; noname = 0
    for y in CUR.finditer(m, start):
        b = y.group(); c = y.start()
        if not (20 in b[:15] and 100 in (b[39], b[40])): continue
        if m[c + L['rep'] - 1] != 2: continue
        seg = m; base = 0
        pid = struct.unpack_from('<I', m, c + L['pid'])[0]
        r1, r2, r3 = struct.unpack_from('<HHH', m, c + L['rep']); ca, pa = struct.unpack_from('<HH', m, c + L['ca'])
        club = struct.unpack_from('<I', m, c + L['club'])[0]
        if not (ca <= 200 and pa <= 200 and r1 <= 10000 and r2 <= 10000 and r3 <= 10000): continue
        e = c + 69
        # el bloque de contrato [id persona = id jugador + 1][club] va justo antes del nombre: enlaza bloque y nombre
        key = struct.pack('<I', pid + 1); k = e; nm = None; tries = 0
        while tries < 40:
            k = m.find(key, k + 1, e + 400000)
            if k < 0: break
            tries += 1
            nm = find_name(m, k, L, FN, SN, CN, 260)
            if nm: break
        if not nm:
            noname += 1; continue
        o, dpos, full = nm
        fn = struct.unpack_from('<I', m, o)[0]; sn = struct.unpack_from('<I', m, o + L['sn'])[0]; cn = struct.unpack_from('<I', m, o + L['cn'])[0]
        sharp = struct.unpack_from('<H', m, e + L['sharp'])[0]; cond = struct.unpack_from('<H', m, e + L['cond'])[0]
        wt, ht = struct.unpack_from('<HH', m, e + L['wt'])
        cclub = struct.unpack_from('<I', m, k + 4)[0]
        wage = struct.unpack_from('<I', m, k + L['wage'])[0] if cclub != 0xffffffff else ''
        nat = struct.unpack_from('<I', m, dpos + 9)[0]
        w.writerow([pid, FN.get(fn, ''), SN.get(sn, ''), CN.get(cn, '') if cn != 0xffffffff else '', full, fn, sn, date(m, dpos), nat, club if club != 0xffffffff else '', ca, pa, r1, r2, r3,
                    ht, wt, cond, sharp, date(m, e + L['joined']), wage, cclub if cclub != 0xffffffff else ''] + list(b[:15]) + list(b[15:]) + [c, o])
        rows += 1
    print('bloques sin ficha de nombre localizada:', noname, file=sys.stderr)
    print('jugadores exportados:', rows, file=sys.stderr)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
