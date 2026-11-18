"""The human manager. humans.dat holds his pid+1 (FM20 at byte 11, FM24 at byte 10); his person record is type 9.
FM24 keeps the name record inside that record (fm_export.find_name from the header, up to ~50 KB in). FM20 keeps it
in the non-player part, right after his contracts: [01 00 6c 07][pid+1][club]... and then the name record.
Name record (same as players): first name / surname / common name ids, birth date, [u8][ethnicity][hair colour]
[hair length][skin], nation u32, personality (FM20 +13, FM24 +17), birth city id+1 (FM20 +21, FM24 +25).
This step copies the identity of the FM20 manager onto the FM24 one (Miguel Mendez over Gumersindo Balaguera):
names, birth date (shifted like everybody else), nationality, birthplace, appearance, personality, and the name
shown in the saved game list (save_game_summary.dat) and in the hall of fame."""
import re, struct, sys, collections
def human_pid(m, h, ver):
    """pid of the human manager: u32 pid+1 in humans.dat whose person record is type 9"""
    import fm_personas_nombre as PN
    for off in range(6, 20):
        v = struct.unpack_from('<I', h, off)[0] - 1
        if 0 < v < 3000000:
            c = PN.cabeceras(m, [v])
            if v in c and m[c[v] + 12] == 9: return v, c[v]
    return None, None
def nombre20(m, pid, L, FN, SN, CN):
    """name record of the FM20 human: the name record that follows [01 00 6c 07][pid+1]"""
    import fm_export as X
    votos = collections.Counter()
    for x in re.finditer(re.escape(b'\x01\x00\x6c\x07' + struct.pack('<I', pid + 1)), m):
        r = X.find_name(m, x.end(), L, FN, SN, CN, 600)
        if r: votos[(r[0], r[1])] += 1
    return votos.most_common(1)[0][0] if votos else None
def bloque(m, o, n, ventana=900):
    """start of the staff attribute block (n values 1-100 followed by ff ff ff ff) before the name record at o"""
    mejor = None
    for x in re.finditer(rb'\xff\xff\xff\xff', m[o - ventana:o]):
        s = o - ventana + x.start() - n
        w = m[s:s + n]
        if all(1 <= c <= 100 for c in w) and len(set(w)) > 2 and m[s - 6:s - 4] == m[s - 6:s - 4] and struct.unpack_from('<H', m, s - 16 if n == 51 else s - 15)[0] <= 10000:
            mejor = s
    return mejor
CAPS = re.compile(rb'(?=([\x00-\xc8][\x00-\x80][\x00-\x80][\x00-\x80])(..[\x6c-\xff]\x07)(..[\x6c-\xff]\x07))', re.S)
def caps(m, o, ventana):
    """caps field of the human: the last [caps][goals][youth][youth][date][date] with a real second date before the
    name record (FM20 ~300 bytes before it, FM24 ~100)"""
    mejor = None
    for x in CAPS.finditer(m, o - ventana, o):
        d1 = struct.unpack_from('<HH', m, x.start(2)); d2 = struct.unpack_from('<HH', m, x.start(3))
        if d2[1] > 1900 and 1 <= (d2[0] & 0x1ff) <= 366 and (d1[1] == 1900 or 1 <= (d1[0] & 0x1ff) <= 366) and m[x.start(1)] > 0:
            mejor = x.start(1)
    return mejor
def paso(src20, entrada, salida, desp):
    import time
    from fmsave import Save
    import fmcontenedor as C, fm_export as X, fm_ciudades as CI
    sys.argv = sys.argv[:1]
    import fm_trasplante as TP
    t0 = time.time()
    S20 = Save(src20); sm = S20.read('game_db.dat'); h20 = S20.read('humans.dat')
    E = C.Contenedor(entrada); dm = bytearray(E.read('game_db.dat')); h24 = E.read('humans.dat')
    Ls, Ld = X.LAY[7], X.LAY[8]
    sFN, sSN, sCN, _, _ = TP.tables(sm); dFN, dSN, dCN, _, _ = TP.tables(bytes(dm))
    p20, _ = human_pid(sm, h20, 7); p24, c24 = human_pid(dm, h24, 8)
    n20 = nombre20(sm, p20, Ls, sFN, sSN, sCN)
    r24 = X.find_name(dm, c24, Ld, dFN, dSN, dCN, 120000)
    if not (n20 and r24): print('manager: no localizado', p20, p24, n20, r24); E.escribir(salida, {}); return
    (o20, d20), (o24, d24) = n20, r24[:2]
    fn = sFN.get(struct.unpack_from('<I', sm, o20)[0], ''); sn = sSN.get(struct.unpack_from('<I', sm, o20 + Ls['sn'])[0], '')
    viejo = (dFN.get(struct.unpack_from('<I', dm, o24)[0], ''), dSN.get(struct.unpack_from('<I', dm, o24 + Ld['sn'])[0], ''))
    rFN = {}; rSN = {}
    for i, s in dFN.items(): rFN.setdefault(s, i)
    for i, s in dSN.items(): rSN.setdefault(s, i)
    notas = []
    if fn in rFN: struct.pack_into('<I', dm, o24, rFN[fn])
    else: notas.append('nombre "%s" no existe en FM24' % fn)
    if sn in rSN: struct.pack_into('<I', dm, o24 + Ld['sn'], rSN[sn])
    else: notas.append('apellido "%s" no existe en FM24' % sn)
    struct.pack_into('<I', dm, o24 + Ld['cn'], 0xffffffff)
    d, y = struct.unpack_from('<HH', sm, d20); d &= 0x1ff; y += desp
    if d == 366 and not (y % 4 == 0 and (y % 100 or y % 400 == 0)): d = 365
    struct.pack_into('<HH', dm, d24, d, y)
    ap = bytearray(sm[d20 + 4:d20 + 9])
    if 1 <= ap[2] <= 6: ap[2] = (7, 9, 11, 13, 15, 11)[ap[2] - 1]
    dm[d24 + 4:d24 + 9] = ap
    dm[d24 + 9:d24 + 13] = sm[d20 + 9:d20 + 13]
    dm[d24 + Ld['pers']:d24 + Ld['pers'] + 8] = sm[d20 + Ls['pers']:d20 + Ls['pers'] + 8]
    ciu, _ = CI.traduccion(CI.ciudades(sm), CI.ciudades(bytes(dm)))
    c20 = struct.unpack_from('<I', sm, d20 + 21)[0]
    struct.pack_into('<I', dm, d24 + 25, ciu.get(c20, 0xffffffff))
    # reputation, ability and staff attributes: [3 reputations u16][current u16][potential u16][formations...]
    # [attributes 1-100] ff ff ff ff, a few hundred bytes before the name record. FM20 has 51 attributes, FM24 53:
    # FM24 adds one at the start (FM20 i -> FM24 i + 1, checked with Pochettino) and one near the end (not mapped)
    a20 = bloque(sm, o20, 51); a24 = bloque(dm, o24, 53)
    if a20 and a24:
        dm[a24 - 15:a24 - 5] = sm[a20 - 16:a20 - 6]
        dm[a24 + 1:a24 + 45] = sm[a20:a20 + 44]
        notas.append('reputacion y atributos')
    else: notas.append('atributos no localizados (%s, %s)' % (a20, a24))
    # international caps and goals: [caps][goals][youth caps][youth goals][date][date]
    k20 = caps(sm, o20, 400); k24 = caps(dm, o24, 400)
    if k20 is not None and k24 is not None:
        dm[k24:k24 + 4] = sm[k20:k20 + 4]
        for k in (4, 8):
            d_, y_ = struct.unpack_from('<HH', sm, k20 + k)
            if y_ > 1900: y_ += desp
            struct.pack_into('<HH', dm, k24 + k, d_, y_)
        notas.append('internacional %d/%d' % (sm[k20], sm[k20 + 1]))
    nuevos = {('', 'game_db.dat'): bytes(dm)}
    # the name in the saved game list and in the hall of fame
    def cad(s): b = s.encode('utf-8'); return struct.pack('<I', len(b)) + b
    for f, pares in (('save_game_summary.dat', [(cad('%s %s' % viejo), cad('%s %s' % (fn, sn)))]),
                     ('hall_of_fame.dat', [(cad(viejo[0]) + cad(viejo[1]), cad(fn) + cad(sn))])):
        try: b = E.read(f)
        except Exception: continue
        n = 0
        for a, c in pares: n += b.count(a); b = b.replace(a, c)
        if n: nuevos[('', f)] = b; notas.append('%s: %d' % (f, n))
    E.escribir(salida, nuevos)
    print('manager: %s %s (FM20 pid %d) sobre %s %s (FM24 pid %d) | nacimiento %d/%d | %s | %.0fs'
          % (fn, sn, p20, viejo[0], viejo[1], p24, d, y, '; '.join(notas), time.time() - t0))
if __name__ == '__main__':
    a = sys.argv[1:]
    paso(a[0], a[1], a[2], int(a[3]))
