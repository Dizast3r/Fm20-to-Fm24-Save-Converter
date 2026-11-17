"""saldo y patrocinios del club. [i8 saldo][01006c07 x3][00 x5][5 x f32][n][n x 24: 01 tipo inicio fin 01 total id 00 por_temporada]"""
import re, struct
TAIL = re.compile(rb'\x01\x00\x6c\x07\x01\x00\x6c\x07\x01\x00\x6c\x07\x00\x00\x00\x00\x00', re.S)
def okd(m, p):
    d, y = struct.unpack_from('<HH', m, p); return 1990 <= y <= 2070 and 1 <= (d & 0x1ff) <= 366
def blocks(m, lo=0, hi=60 << 20):
    out = []
    for x in TAIL.finditer(m, lo, hi):
        bal = x.start() - 8; cnt = x.end() + 20; n = m[cnt]
        if n > 40: continue
        ok = True
        for i in range(n):
            r = cnt + 1 + 24 * i
            if m[r] != 1 or m[r + 10] > 1 or not okd(m, r + 2) or not okd(m, r + 6): ok = False; break
        if not ok: continue
        if n == 0 and m[cnt + 1] not in (0, 1, 2, 3, 4, 5): continue
        out.append(dict(bal=bal, cnt=cnt, n=n))
    return out

def by_club20(m, ts, lo=0, hi=60 << 20):
    """FM20: tras la lista viene el registro de nombres del club con sus ids de equipo; el primero da el id unico"""
    out = {}
    for b in blocks(m, lo, hi):
        end = b['cnt'] + 1 + 24 * b['n']
        for x in re.finditer(rb'\x01\x01[\x00-\x03]', m[end:end + 600]):
            p = end + x.end(); n = struct.unpack_from('<I', m, p)[0]
            if not 0 < n < 120: continue
            q = p + 4 + n; n2 = struct.unpack_from('<I', m, q)[0]
            if not 0 < n2 < 80: continue
            r = q + 4 + n2; k = m[r]
            if not 0 < k <= 12: continue
            t = struct.unpack_from('<I', m, r + 1)[0]
            if t in ts: out.setdefault(ts[t]['uid'], b)
            break
    return out

def by_club24(m, clubs, lo=0, hi=60 << 20):
    """FM24: la ficha del club (con sus nombres) va justo antes del saldo"""
    import bisect
    cl = sorted(clubs, key=lambda c: c['after']); ends = [c['after'] for c in cl]; out = {}
    for b in blocks(m, lo, hi):
        i = bisect.bisect_right(ends, b['bal']) - 1
        if i >= 0 and b['bal'] - ends[i] < 4000:
            u = cl[i]['uid']
            if u not in out or b['n'] > out[u]['n']: out[u] = b
    return out
