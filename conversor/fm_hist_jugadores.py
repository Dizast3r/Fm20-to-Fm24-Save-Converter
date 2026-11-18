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
def transferir(ls20, dt20, ls24, dt24, mapa, u20, u24, cm, desp):
    L20, _, _, a0 = T.leer(ls20); L24, cab, cola, b0 = T.leer(ls24)
    R20 = T.tam_fila(ls20); R24 = T.tam_fila(ls24)
    inv = {}
    for t, u in sorted(u24.items()): inv.setdefault(u, t)
    def t24(t): return inv.get(u20.get(t), 0xffffffff)
    dt = bytearray(dt24); listas = [list(l) for l in L24]; est = collections.Counter()
    for t, v in mapa:
        if v >= len(L20): est['lista FM20 inexistente'] += 1; continue
        offs = []
        filas = [convertir(dt20[a0 + o:a0 + o + R20], t24, cm, desp) for o in L20[v]]
        filas.sort(key=lambda r: struct.unpack_from('<H', r, 11)[0])   # FM24 keeps every list in season order
        for r in filas:
            offs.append(len(dt) - b0); dt += r
        while len(listas) <= t: listas.append([])
        listas[t] = offs; est['jugadores'] += 1; est['temporadas'] += len(offs)
    return T.escribir(cab, listas, cola), bytes(dt), est
