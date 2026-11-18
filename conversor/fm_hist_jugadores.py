"""Player career history (player_stats_hist): one list per player, rows of 96 bytes (FM20) / 152 bytes (FM24):
[00][team u32][division u16][u32 ffffffff][year u16 (season start)][stats...]. The first 69 bytes of stats
(starts, sub appearances, goals, assists, player of the match, rating, ...) have the same layout in both versions;
FM24 adds more fields at the end (left at 0).
The list of each player is chosen in fm_trasplante (u32 21 bytes before the name record) and written to
historial_jugadores.json as (FM24 list, FM20 list)."""
import struct, collections
import fm_tad as T
COMUN = (13, 82)
def convertir(r20, t24, cm, desp):
    r = bytearray(152)
    team = struct.unpack_from('<I', r20, 1)[0]; comp = struct.unpack_from('<H', r20, 5)[0]
    otro = struct.unpack_from('<I', r20, 7)[0]; y = struct.unpack_from('<H', r20, 11)[0]
    struct.pack_into('<I', r, 1, t24(team)); struct.pack_into('<H', r, 5, cm.get(comp, 0xffff) if comp != 0xffff else 0xffff)
    struct.pack_into('<I', r, 7, t24(otro) if otro != 0xffffffff else 0xffffffff)
    struct.pack_into('<H', r, 11, y + desp if 1900 < y < 2100 else y)
    r[COMUN[0]:COMUN[1]] = r20[COMUN[0]:COMUN[1]]
    return bytes(r)
def transferir(ls20, dt20, ls24, dt24, mapa, u20, u24, cm, desp, ps20=None):
    L20, _, _, a0 = T.leer(ls20); L24, cab, cola, b0 = T.leer(ls24)
    cur = actuales(ps20, [m[2] for m in mapa if len(m) > 2]) if ps20 else {}
    ycur = max(struct.unpack_from('<H', dt20, a0 + o + 11)[0] for l in L20[::97] for o in l) + 1
    R20 = T.tam_fila(ls20); R24 = T.tam_fila(ls24)
    inv = {}
    for t, u in sorted(u24.items()): inv.setdefault(u, t)
    def t24(t): return inv.get(u20.get(t), 0xffffffff)
    dt = bytearray(dt24); listas = [list(l) for l in L24]; est = collections.Counter()
    for m_ in mapa:
        t, v = m_[0], m_[1]
        if v >= len(L20): est['lista FM20 inexistente'] += 1; continue
        offs = []
        r20 = [dt20[a0 + o:a0 + o + R20] for o in L20[v]]
        if len(m_) > 2 and m_[2] in cur:
            ult = max(r20, key=lambda r: struct.unpack_from('<H', r, 11)[0]) if r20 else None
            comp = struct.unpack_from('<H', ult, 5)[0] if ult else 0xffff
            nuevas = filas_actuales(ps20, cur[m_[2]], ycur, comp)
            r20 = [r for r in r20 if struct.unpack_from('<H', r, 11)[0] < ycur] + nuevas
            est['temporada en curso'] += 1 if nuevas else 0
        filas = [convertir(r, t24, cm, desp) for r in r20]
        filas.sort(key=lambda r: struct.unpack_from('<H', r, 11)[0])   # FM24 keeps every list in season order
        for r in filas:
            offs.append(len(dt) - b0); dt += r
        while len(listas) <= t: listas.append([])
        listas[t] = offs; est['jugadores'] += 1; est['temporadas'] += len(offs)
    return T.escribir(cab, listas, cola), bytes(dt), est

# --- season in progress: player_stats.dat (rgman) keeps, per player, [01][pid+1][club u32]... and from byte 23 one
# 83-byte block per competition type (friendlies, league, cup, continental, international, ...):
# [rating sum x10 u16][minutes u16][starts][subs][apps][goals][assists][?][pens][pen goals][MoM][12 bytes][56 bytes
# with the same layout as bytes 40..95 of a history row]
import numpy as np
def actuales(ps, pids):
    a = np.frombuffer(ps, dtype=np.uint8); out = {}
    want = np.array(sorted(p + 1 for p in pids), dtype=np.uint32)
    for al in range(4):
        n = (len(ps) - 1 - al) // 4
        x = np.frombuffer(ps, dtype=np.uint32, count=n, offset=1 + al)
        q = np.searchsorted(want, x); q[q >= len(want)] = 0
        for i in np.nonzero((want[q] == x))[0]:
            k = al + 4 * int(i)
            if ps[k] == 1: out.setdefault(int(x[i]) - 1, k)
    return out
def filas_actuales(ps, k, year, comp):
    club = struct.unpack_from('<I', ps, k + 5)[0]; filas = []
    for tipo in range(5):
        s = k + 23 + 83 * tipo
        if s + 83 > len(ps) or ps[s - 2:s] != b'\x01\x01': break
        st, sb, ap = ps[s + 4], ps[s + 5], ps[s + 6]
        if ap != st + sb: break
        if ap == 0: continue
        r = bytearray(96); r[0] = 0
        struct.pack_into('<IHIH', r, 1, club, comp, 0xffffffff, year)
        r[13:17] = ps[s:s + 4]; r[18] = ps[s + 10]; r[19] = ps[s + 11]
        r[23] = ap; r[24] = st; r[25] = sb; r[26] = ap; r[27] = ps[s + 7]; r[28] = ps[s + 8]; r[29] = ps[s + 12]; r[31] = tipo
        r[40:96] = ps[s + 25:s + 81]
        filas.append(bytes(r))
    return filas
