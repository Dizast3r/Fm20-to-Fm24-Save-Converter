"""presupuestos del club (en GBP): fichajes original y actual, salarial semanal. Clave: id unico del club"""
import re, struct
HP = re.compile(rb'(?=(.{4})(.{4})\2\x00(.{4}).{8}\3)', re.S)
def budgets_all(m, ver, lo=0, hi=60 << 20):
    """uid -> posiciones de presupuestos, probando cada aparicion de la cabecera"""
    f = budgets24 if ver == 8 else budgets20; out = {}
    for x in HP.finditer(m, lo, hi):
        uid = struct.unpack('<I', x.group(2))[0]
        if uid >= 90000000 or uid in out: continue
        if ver == 8 and m[x.start(2) + 13:x.start(2) + 17] != b'\xff' * 4: continue
        g = f(m, x.start(2))
        if g: out[uid] = g
    return out
def heads(m, lo=0, hi=60 << 20):
    out = {}
    for x in HP.finditer(m, lo, hi):
        uid = struct.unpack('<I', x.group(2))[0]
        if uid < 90000000: out.setdefault(uid, x.start(2))
    return out
def budgets24(m, p):
    n = struct.unpack_from('<I', m, p + 35)[0]
    if not 0 < n < 120: return None
    q = p + 39 + n; n2 = struct.unpack_from('<I', m, q)[0]
    if not 0 < n2 < 80: return None
    a = q + 4 + n2; k = m[a + 8]
    if m[a] != 1 or k > 40: return None
    one = a + 9 + 4 * k
    if m[one] != 1: return None
    return dict(one=one, orig=one + 1, cur=one + 5, wage=one + 67)
def budgets20(m, p):
    for one in range(p + 29, p + 160):
        if m[one] != 1: continue
        o, c = struct.unpack_from('<ii', m, one + 1)
        if not (0 <= c and 0 <= o < 2**31): continue
        w = struct.unpack_from('<i', m, one + 63)[0]
        if not 0 <= w < 50_000_000: continue
        for n in range(0, 30):
            st = one - 4 * n - 1
            if st < p + 25: break
            if m[st] == n and all(struct.unpack_from('<I', m, st + 1 + 4 * i)[0] < 10_000_000 for i in range(n)):
                return dict(one=one, orig=one + 1, cur=one + 5, wage=one + 63)
    return None
