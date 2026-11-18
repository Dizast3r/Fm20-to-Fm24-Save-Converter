"""Club affiliations (club information > affiliated clubs: B team, feeder clubs, loan partners...).
One table near the end of game_db.dat: [count u32] + count records
FM20 43 bytes: [parent club id+1][options, 5 bytes][affiliate club id+1][start date][end date][u32 flags]
               [annual fee u32, pounds][32 32][date][ff ff ff 00][u32]
FM24 47 bytes: the same plus a date at the end (null in the template).
The 5 option bytes are a bit field shared by both versions (04 c2 c5 80 00 = B team, 03 25 02 00 00 = loans +
youth + fee...). Every affiliation between two clubs that exist in FM20 is taken from FM20; the template keeps only
the ones of FM24 clubs with no FM20 equivalent."""
import re, struct, sys, collections
NULO = b'\x01\x00\x6c\x07'
def _ok(m, k, R):
    if k < 0 or k + R > len(m) or m[k + 29:k + 31] != b'22': return False
    y1 = struct.unpack_from('<H', m, k + 15)[0]; y2 = struct.unpack_from('<H', m, k + 19)[0]
    return 1900 <= y1 <= 2100 and 1900 <= y2 <= 2100 and 0 < struct.unpack_from('<I', m, k)[0] < 500000
def localizar(m, R):
    """(position of the count, count)"""
    vistos = set()
    for x in re.finditer(re.escape(b'22' + NULO + b'\xff\xff\xff\x00'), m):
        k = x.start() - 29
        if k in vistos or not _ok(m, k, R): continue
        p = k
        while _ok(m, p - R, R): p -= R
        n = 0
        while _ok(m, p + R * n, R): n += 1
        vistos.update(range(p, p + R * n, R))
        if n >= 10 and struct.unpack_from('<I', m, p - 4)[0] == n: return p - 4, n
    return None
def _fecha(b, k, desp):
    d, y = struct.unpack_from('<HH', b, k)
    if y <= 1900 or y >= 2100: return
    y += desp
    if (d & 0x1ff) == 366 and not (y % 4 == 0 and (y % 100 or y % 400 == 0)): d = (d & ~0x1ff) | 365
    struct.pack_into('<HH', b, k, d, y)
def paso(src20, entrada, salida, desp):
    import time
    from fmsave import Save
    import fmcontenedor as C, fm_uids as U, fm_plazos as PL
    t0 = time.time(); est = collections.Counter()
    sm = Save(src20).read('game_db.dat'); E = C.Contenedor(entrada); dm = E.read('game_db.dat')
    tr = U.traduccion(sm, dm)[0]
    id20 = PL.ids_clubes(sm); id24 = PL.ids_clubes(dm)
    club = {}
    for u, i in id20.items():
        u2 = tr.get(u, u)
        if u2 is not None and u2 in id24: club[i] = id24[u2]
    con20 = set(club.values())
    p20, n20 = localizar(sm, 43); p24, n24 = localizar(dm, 47)
    nuevas = []
    for i in range(n24):   # template affiliations of FM24-only clubs
        r = dm[p24 + 4 + 47 * i:p24 + 4 + 47 * (i + 1)]
        a, c = struct.unpack_from('<I', r, 0)[0] - 1, struct.unpack_from('<I', r, 9)[0] - 1
        if a in con20 and c in con20: est['plantilla descartadas'] += 1
        else: nuevas.append(r); est['plantilla conservadas'] += 1
    for i in range(n20):
        b = bytearray(sm[p20 + 4 + 43 * i:p20 + 4 + 43 * (i + 1)]) + NULO
        a, c = struct.unpack_from('<I', b, 0)[0] - 1, struct.unpack_from('<I', b, 9)[0] - 1
        if a not in club or c not in club: est['FM20 sin club equivalente'] += 1; continue
        struct.pack_into('<I', b, 0, club[a] + 1); struct.pack_into('<I', b, 9, club[c] + 1)
        for k in (13, 17, 31): _fecha(b, k, desp)
        nuevas.append(bytes(b)); est['FM20'] += 1
    nm = dm[:p24] + struct.pack('<I', len(nuevas)) + b''.join(nuevas) + dm[p24 + 4 + 47 * n24:]
    E.escribir(salida, {('', 'game_db.dat'): nm})
    print('clubes afiliados: FM20 %d, plantilla %d | ' % (n20, n24) + ' | '.join('%s %d' % kv for kv in est.items()) + ' | %.0fs' % (time.time() - t0))
if __name__ == '__main__':
    a = sys.argv[1:]
    paso(a[0], a[1], a[2], int(a[3]))
