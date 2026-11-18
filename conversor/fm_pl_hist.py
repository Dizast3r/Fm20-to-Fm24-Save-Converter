"""Database career history of the players (seasons before the game started: "2016/17 Pro Vercelli 0 apps").
FM24 keeps it in pl_hist_ls.dat / pl_hist_dt.cmt (a 'tad' list per player, rows of 40 bytes
[from year u16][to year u16][u8 type][apps u8][goals u8][fee i32][club uid+1][club uid+1][...]); a table in
game_db, sorted by unique id, gives [uid u32][list - 1 u32] (the 2023 template has none, a save played for years has
it). A transplanted player kept the history of the FM24 player whose record he took. Now his list gets the database
history of the same real player in FM24 (seasons before the FM20 game started), or nothing (regens)."""
import struct, collections, bisect
import numpy as np
def tabla(m, nlistas, muestra):
    """{uid: list} from the [uid][list - 1] table; `muestra` = some uids that should be in it"""
    for u in muestra:
        k = struct.pack('<I', u); p = m.find(k)
        while p >= 0:
            if p % 1 == 0 and p + 8 <= len(m):
                v = struct.unpack_from('<I', m, p + 4)[0]
                ok = v < nlistas and all(struct.unpack_from('<I', m, p + 8 * i)[0] < struct.unpack_from('<I', m, p + 8 * (i + 1))[0] for i in range(-3, 3))
                if ok:
                    a = p
                    while a >= 8 and struct.unpack_from('<I', m, a - 8)[0] < struct.unpack_from('<I', m, a)[0] and struct.unpack_from('<I', m, a - 4)[0] < nlistas: a -= 8
                    b = p
                    while b + 16 <= len(m) and struct.unpack_from('<I', m, b + 8)[0] > struct.unpack_from('<I', m, b)[0] and struct.unpack_from('<I', m, b + 12)[0] < nlistas: b += 8
                    n = (b - a) // 8 + 1
                    if n > 1000:
                        arr = np.frombuffer(m, dtype=np.uint32, count=2 * n, offset=a)
                        return dict(zip(arr[0::2].tolist(), (arr[1::2] + 1).tolist()))
            p = m.find(k, p + 1)
    return {}
def transferir(ls, dt, pares, host_uid, uid20, tab, inicio):
    """pares: [(FM20 pid, FM24 host pid)]; host_uid: {FM24 pid: uid before the transplant}; uid20: {FM20 pid: uid};
    inicio: first season of the FM20 game (rows from it on come from FM20's own history)"""
    import fm_tad as T
    L, cab, cola, d0 = T.leer(ls); R = T.tam_fila(ls)
    extra = bytearray(); base = len(dt) - d0; est = collections.Counter()
    for a, h in pares:
        lh = tab.get(host_uid.get(h))
        if lh is None or lh >= len(L): est['sin lista'] += 1; continue
        ls_ = tab.get(uid20.get(a))
        filas = []
        if ls_ is not None and ls_ < len(L) and ls_ != lh:
            filas = [dt[d0 + o:d0 + o + R] for o in L[ls_] if d0 + o + R <= len(dt) and struct.unpack_from('<H', dt, d0 + o)[0] < inicio]
        offs = []
        for r in filas: offs.append(base + len(extra)); extra += r
        L[lh] = offs; est['con historial real' if filas else 'vaciadas'] += 1
    return T.escribir(cab, L, cola), dt + bytes(extra), est
