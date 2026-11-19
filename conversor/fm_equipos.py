"""fichas de equipo: id de equipo (el id_club de los jugadores), id unico, division actual y anterior, lista de plantilla"""
import re, struct
PAT = re.compile(rb'(.{4})(.{4})\2\x0a\x00.{3}(.{4})(.{4})', re.S)
def teams(m, lo, hi):
    out = {}
    for x in PAT.finditer(m, lo, hi):
        t = struct.unpack('<I', x.group(1))[0] + 1; uid = struct.unpack('<I', x.group(2))[0]
        div = struct.unpack('<I', x.group(3))[0]; last = struct.unpack('<I', x.group(4))[0]
        if t > 400000 or uid > 90000000: continue
        out.setdefault(t, dict(pos=x.start(), uid=uid, div=div, last=last, divpos=x.start() + 17))
    return out

def tabla(m):
    """{team id: position of its record}: the team table of game_db, [team - 1][uid][uid][0a / 0b], one record per
    team id from 1 up, in id order (FM24 2031: 46190 records between 88 and 93 MB). The header pattern also matches
    elsewhere (person and competition records, runs of equal bytes) and the first match of a team is often not its
    record: the table is the longest run of matches whose team id grows with the position, cut at the first gap
    of more than 1 MB. Teams created during the game (ids past the table) are kept elsewhere and not returned."""
    import numpy as np, bisect
    P = []; T = []; b = np.frombuffer(m, dtype=np.uint8)
    for al in range(4):
        n = (len(m) - al) // 4 - 3; a = np.frombuffer(m, dtype=np.uint32, count=n + 3, offset=al)
        ok = (a[:n] < 400000) & (a[1:n + 1] == a[2:n + 2]) & (a[1:n + 1] > 0) & (a[1:n + 1] < 0x7fffffff)
        idx = np.nonzero(ok)[0]; pos = al + 4 * idx; dentro = pos + 12 < len(m); idx = idx[dentro]; pos = pos[dentro]
        tipo = b[pos + 12]; sel = (tipo == 10) | (tipo == 11)
        P.append(pos[sel]); T.append(a[idx][sel])
    P = np.concatenate(P); T = np.concatenate(T); o = np.argsort(P, kind='stable'); P = P[o].tolist(); T = T[o].tolist()
    tails = []; ti = []; prev = [-1] * len(P)
    for i, t in enumerate(T):   # longest chain with a strictly growing team id (patience sorting)
        k = bisect.bisect_left(tails, t)
        if k == len(tails): tails.append(t); ti.append(i)
        else: tails[k] = t; ti[k] = i
        prev[i] = ti[k - 1] if k else -1
    ch = []; i = ti[-1] if ti else -1
    while i >= 0: ch.append(i); i = prev[i]
    ch.reverse()
    segs = []; s = 0   # the table is the biggest piece of the chain without a gap of more than 1 MB
    for j in range(1, len(ch) + 1):
        if j == len(ch) or P[ch[j]] - P[ch[j - 1]] > 1 << 20: segs.append(ch[s:j]); s = j
    mejor = max(segs, key=len) if segs else []
    return {T[i] + 1: P[i] for i in mejor}
