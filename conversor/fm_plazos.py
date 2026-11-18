"""Transfer fees paid in installments (club information > finances > transfer debt: "X still owes N installments of Y").
transfer_man.dat keeps them as one list, the same in FM20 and FM24: [count u32] + count x 27 bytes
[03][monthly amount u32 (pounds)][payer club id+1 u32][receiver club id+1 u32][date of the transfer]
[months left u8][pid+1 u32][interval in months u8 (12 yearly, 6, 1)][date]
The installment shown in the game is the monthly amount x interval (Cerofolini: 1388888 x 12 = 16.67M pounds a year).
The FM24 list of the template is replaced by the FM20 one (players through pares.txt, clubs through their unique id)."""
import re, struct, sys, collections
R = 27
def _ok(t, k):
    if k < 0 or k + R > len(t) or t[k] != 3: return False
    c1, c2 = struct.unpack_from('<II', t, k + 5)
    y1 = struct.unpack_from('<H', t, k + 15)[0]; pid = struct.unpack_from('<I', t, k + 18)[0]; y2 = struct.unpack_from('<H', t, k + 25)[0]
    return 0 < c1 < 500000 and 0 < c2 < 500000 and 1900 <= y1 <= 2100 and 1900 <= y2 <= 2100 and 0 < pid < 5000000 and t[k + 22] in (1, 2, 3, 4, 6, 12)
SEMILLA = re.compile(rb'(?=\x03.{12}...[\x07\x08].{5}[\x01\x02\x03\x04\x06\x0c]...[\x07\x08]\x03)', re.S)
def localizar(t):
    """(position of the count, count) of the installment list"""
    vistos = set()
    for x in SEMILLA.finditer(t):
        k = x.start()
        if k in vistos or not _ok(t, k): continue
        p = k
        while _ok(t, p - R): p -= R
        n = 0
        while _ok(t, p + R * n): n += 1
        vistos.update(range(p, p + R * n, R))
        if p >= 4 and struct.unpack_from('<I', t, p - 4)[0] == n and n >= 3: return p - 4, n
    return None
def leer(t):
    r = localizar(t)
    if r is None: return None, []
    p, n = r
    return r, [bytearray(t[p + 4 + R * i:p + 4 + R * (i + 1)]) for i in range(n)]
def _fecha(b, k, desp):
    d, y = struct.unpack_from('<HH', b, k)
    if y <= 1900: return
    y += desp
    if (d & 0x1ff) == 366 and not (y % 4 == 0 and (y % 100 or y % 400 == 0)): d = (d & ~0x1ff) | 365
    struct.pack_into('<HH', b, k, d, y)
def ids_clubes(m):
    """{club uid: club record id}"""
    import fm_clubnames as N
    out = {}
    for p, u, _ in N.cabeceras(m): out.setdefault(u, struct.unpack_from('<I', m, p)[0])
    return out
def paso(src20, entrada, salida, pares_txt, desp):
    import time
    from fmsave import Save
    import fmcontenedor as C, fm_uids as U
    t0 = time.time(); est = collections.Counter()
    s20 = Save(src20); sm = s20.read_mmap('game_db.dat'); t20 = s20.read('transfer_man.dat')
    E = C.Contenedor(entrada); dm = E.read('game_db.dat'); t24 = E.read('transfer_man.dat')
    pm = {}
    for a in open(pares_txt).read().split():
        v = [int(x) for x in a.split(':')]; pm[v[0]] = v[1]
    tr = U.traduccion(sm, dm)[0]
    id20 = ids_clubes(sm); id24 = ids_clubes(dm)
    club = {}
    for u, i in id20.items():
        u2 = tr.get(u, u)
        if u2 is not None and u2 in id24: club[i] = id24[u2]
    (p24, n24), _ = leer(t24)
    _, es20 = leer(t20)
    nuevas = []
    for b in es20:
        c1, c2 = struct.unpack_from('<II', b, 1 + 4); pid = struct.unpack_from('<I', b, 18)[0] - 1
        if c1 - 1 not in club or c2 - 1 not in club: est['club sin equivalente'] += 1; continue
        if pid not in pm: est['jugador sin convertir'] += 1; continue
        struct.pack_into('<II', b, 5, club[c1 - 1] + 1, club[c2 - 1] + 1)
        struct.pack_into('<I', b, 18, pm[pid] + 1)
        _fecha(b, 13, desp); _fecha(b, 23, desp)
        nuevas.append(bytes(b)); est['plazos'] += 1
    nt = t24[:p24] + struct.pack('<I', len(nuevas)) + b''.join(nuevas) + t24[p24 + 4 + R * n24:]
    E.escribir(salida, {('', 'transfer_man.dat'): nt})
    print('traspasos a plazos: FM20 %d, plantilla FM24 %d (descartados) | ' % (len(es20), n24) + ' | '.join('%s %d' % kv for kv in est.items()) + ' | %.0fs' % (time.time() - t0))
if __name__ == '__main__':
    a = sys.argv[1:]
    paso(a[0], a[1], a[2], a[3], int(a[4]))
