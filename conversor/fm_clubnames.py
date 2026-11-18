"""Club table: uid -> (nation, full name, short name), FM20 and FM24.
Header [club id][uid][uid] 00 + 4 u32 that are the nation or ffffffff (e.g. FM24 [nation][ff][nation][nation]); the names come later in the same record
(after a variable amount of data, up to several KB for big clubs): the first [len u32][full][len u32][short] pair."""
import re, struct
CAB = re.compile(rb'(?=(.{4})(.{4})\2\x00(.{16}))', re.S)
NOM = re.compile(rb'\x00\x01\x01', re.S)
PAR = re.compile(rb'[\x02-\x77]\x00\x00\x00[\x30-\x39\x41-\x5a\xc3-\xc5\x27\x22]', re.S)   # [len u32] + full name starting with a capital/digit
def _cadena(m, p):
    n = struct.unpack_from('<I', m, p)[0]
    if not 0 < n < 120: return None, p
    try: return m[p + 4:p + 4 + n].decode('utf-8'), p + 4 + n
    except UnicodeDecodeError: return None, p
def cabeceras(m, hi=200 << 20, hueco=16 << 20):
    """[(position, uid, nation)] of the club records, in file order. The table is near the start of game_db
    (FM20/FM24 template < 40 MB, a FM24 save played for 8 years up to ~90 MB): it ends at the first gap of more than
    `hueco` bytes without a header"""
    cabs = []; ultimo = -1
    for x in CAB.finditer(m, 0, min(len(m), hi)):
        a, u = struct.unpack('<II', x.group(1) + x.group(2)); v = struct.unpack('<4I', x.group(3))
        nat = [w for w in v if w != 0xffffffff]
        if not (a < 400000 and 0 < u < 0x7fffffff and len(nat) >= 2 and len(set(nat)) == 1 and 0 < nat[0] < 300): continue
        if len(cabs) > 1000 and x.start() - cabs[-1][0] > hueco: break
        if cabs and not 0 < a - ultimo <= 50: continue   # club ids grow along the table; anything else is noise
        cabs.append((x.start(), u, nat[0])); ultimo = a
    return cabs
def nombres(m, hi=200 << 20):
    cabs = cabeceras(m, hi)
    out = {}
    for i, (p, u, n) in enumerate(cabs):
        fin = cabs[i + 1][0] if i + 1 < len(cabs) else p + 200000
        r = None
        for y in NOM.finditer(m, p + 12, fin):          # usual place: after 00 01 01 [u8]
            for k in (3, 4):
                larga, q = _cadena(m, y.start() + k)
                corta, _ = _cadena(m, q) if larga else (None, 0)
                if larga and corta is not None and larga.isprintable() and corta.isprintable(): r = (n, larga, corta); break
            if r: break
        y = None if r else PAR.search(m, p + 12, fin)  # otherwise the first [len][name][len][name] pair
        while y:
            larga, q = _cadena(m, y.start())
            corta, _ = _cadena(m, q) if larga else (None, 0)
            if larga and corta is not None and larga.isprintable() and corta.isprintable(): r = (n, larga, corta); break
            y = PAR.search(m, y.start() + 1, fin)
        if r: out.setdefault(u, r)
    return out
def norm(s): return ' '.join(s.lower().replace('.', ' ').replace('-', ' ').split())
import difflib, collections
def parecidos(a, b):
    a, b = norm(a), norm(b)
    if not a or not b: return False
    if a == b or (len(a) >= 4 and a in b) or (len(b) >= 4 and b in a): return True
    return difflib.SequenceMatcher(None, a, b).ratio() >= 0.75
def igual(x, y):
    """x, y: (nation, full, short)"""
    return x[0] == y[0] and (parecidos(x[1], y[1]) or parecidos(x[2], y[2]) or parecidos(x[1], y[2]) or parecidos(x[2], y[1]))
def traduccion(n20, n24):
    """FM20 club uid -> FM24 club uid. Most uids are stable, but some clubs got another uid in FM24 and their old uid
    may now belong to another club (Rennes 883 -> 881, and 881 was Poitiers in FM20). Rules:
      - same uid and similar name (same nation) -> same uid
      - otherwise a unique FM24 club with the same nation and name -> that club
      - otherwise the same uid if FM24 has it in the same nation and no other FM20 club claims it by name
        (FM20 had unlicensed names: "FCP", "A. Madrid", "Real Hispalis"...)
      - otherwise None (no equivalent)
    Returns {uid20: uid24 or None} and statistics."""
    idx = collections.defaultdict(set)
    for u, (n, l, c) in n24.items():
        idx[(n, norm(l))].add(u); idx[(n, norm(c))].add(u)
    mismo = {u for u, x in n20.items() if u in n24 and igual(x, n24[u])}
    reclamo = {}
    for u, x in n20.items():
        if u in mismo: continue
        cand = (idx.get((x[0], norm(x[1]))) or set()) - mismo          # full name first, then short name
        if len(cand) != 1: cand = (idx.get((x[0], norm(x[2]))) or set()) - mismo
        if len(cand) == 1: reclamo[u] = next(iter(cand))
    veces = collections.Counter(reclamo.values())
    reclamo = {u: v for u, v in reclamo.items() if veces[v] == 1}
    reclamados = set(reclamo.values())
    out = {}; est = collections.Counter()
    for u, x in n20.items():
        if u in mismo: out[u] = u; est['mismo uid'] += 1
        elif u in reclamo: out[u] = reclamo[u]; est['por nombre'] += 1
        elif u in n24 and n24[u][0] == x[0] and u not in reclamados: out[u] = u; est['mismo uid, otro nombre'] += 1
        elif u in n24: out[u] = None; est['uid de otro club'] += 1
        else: out[u] = None; est['sin equivalente'] += 1
    return out, est
