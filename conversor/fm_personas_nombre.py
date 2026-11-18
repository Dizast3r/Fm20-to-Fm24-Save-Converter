"""People whose unique id changed between FM20 and FM24 (e.g. Pochettino 4058 -> 4054): matched by
first name + surname + birth date. Record [pid][uid][uid][type], then (a few hundred bytes later) the name record
[first name id][surname id][common name id][len][full name][birth date]... (fm_export.find_name)."""
import re, struct, collections
import numpy as np
import fm_export as X
TIPOS = {0x01, 0x02, 0x05, 0x09, 0x10, 0x13}
PRIORIDAD = {0x01: 0, 0x02: 0, 0x05: 1, 0x09: 1, 0x10: 2, 0x13: 2}   # the small 0x10 / 0x13 records are not the person
CAB = re.compile(rb'(?=(.{4})(.{4})\2(.))', re.S)
def cabeceras(m, pids):
    """{pid: position of the record [pid][uid][uid][type]} for the given person ids"""
    ks = np.array(sorted(set(pids)), dtype=np.uint32); out = {}
    for al in range(4):
        n = (len(m) - al) // 4 - 3; a = np.frombuffer(m, dtype=np.uint32, count=n + 3, offset=al)
        ok = (a[1:n + 1] == a[2:n + 2]) & (a[1:n + 1] != 0) & (a[1:n + 1] != a[:n])
        cand = np.nonzero(ok)[0]
        v = a[cand]; q = np.searchsorted(ks, v); q[q >= len(ks)] = 0
        for i in cand[ks[q] == v].tolist():
            p = al + 4 * i
            t = m[p + 12]
            if t in TIPOS and a[i + 1] < 0x7fffffff:
                pr = PRIORIDAD.get(t, 9); k = int(a[i])
                if k not in out or pr < out[k][0]: out[k] = (pr, p)
    return {k: p for k, (pr, p) in out.items()}
def clave(m, p, L, FN, SN, CN, span=1500):
    r = X.find_name(m, p, L, FN, SN, CN, span)
    if not r: return None
    q, d, full = r
    for x in CAB.finditer(m, p + 16, q):   # the name found must belong to this record, not to the next person
        i, u = struct.unpack('<II', x.group(1) + x.group(2))
        if x.group(3)[0] in TIPOS and 0 < u < 0x7fffffff and i < 2000000 and u != i and not 0x76c <= u >> 16 <= 0x834: return None
    fn, sn = struct.unpack_from('<I', m, q)[0], struct.unpack_from('<I', m, q + L['sn'])[0]
    dd, y = struct.unpack_from('<HH', m, d)
    return (FN.get(fn, ''), SN.get(sn, ''), dd & 0x1ff, y)
def buscar(m, claves, L, FN, SN, CN):
    """{key: pid} in m for keys (first name, surname, day, year); keys with several candidates are left out"""
    rFN = collections.defaultdict(set); rSN = collections.defaultdict(set)
    for i, s in FN.items(): rFN[s].add(i)
    for i, s in SN.items(): rSN[s].add(i)
    quiero = collections.defaultdict(list)
    for k in claves:
        for a in rFN.get(k[0], ()):
            for b in rSN.get(k[1], ()): quiero[(a, b)].append(k)
    if not quiero: return {}
    fa = np.array(sorted({a for a, b in quiero}), dtype=np.uint32); sb = np.array(sorted({b for a, b in quiero}), dtype=np.uint32)
    hits = []; so = L['sn']
    A = [np.frombuffer(m, dtype=np.uint32, count=(len(m) - al) // 4, offset=al) for al in range(4)]
    for al in range(4):
        al2, sh = (al + so) % 4, (al + so) // 4
        N = min(len(A[al]), len(A[al2]) - sh)
        mask = np.isin(A[al][:N], fa) & np.isin(A[al2][sh:sh + N], sb)
        hits += (al + 4 * np.nonzero(mask)[0]).tolist()
    cand = collections.defaultdict(set)
    for p in hits:
        fn, sn = struct.unpack_from('<I', m, p)[0], struct.unpack_from('<I', m, p + L['sn'])[0]
        if (fn, sn) not in quiero: continue
        r = X.find_name(m, p - 12, L, FN, SN, CN, 13)
        if not r: continue
        dd, y = struct.unpack_from('<HH', m, r[1]); k = (FN[fn], SN[sn], dd & 0x1ff, y)
        if k not in set(quiero[(fn, sn)]): continue
        seg = m[max(0, p - 3000):p]; pid = None
        for x in CAB.finditer(seg):
            i, u = struct.unpack('<II', x.group(1) + x.group(2))
            if x.group(3)[0] in TIPOS and 0 < u < 0x7fffffff and i < 2000000 and u != i: pid = i
        if pid is not None: cand[k].add(pid)
    return {k: next(iter(v)) for k, v in cand.items() if len(v) == 1}
