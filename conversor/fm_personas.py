"""id de persona -> uid para cualquier persona (jugador, retirado, tecnico...): registro [id][uid][uid] en game_db.
Busca solo los ids pedidos; si un id aparece con varios uid se queda con el de registro de persona (mas frecuente)."""
import numpy as np, mmap, collections
def mapa(path, ids, tipos=None):
    f = open(path, 'rb'); m = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    ks = np.array(sorted(set(ids)), dtype=np.uint32); out = collections.defaultdict(collections.Counter)
    W = 8 << 20
    for al in range(4):
        n = (len(m) - al) // 4; a = np.frombuffer(m, dtype=np.uint32, count=n, offset=al)
        for s in range(0, n - 2, W):
            blk = a[s:min(n, s + W + 2)]; k = len(blk) - 2
            ok = (blk[1:k + 1] == blk[2:k + 2]) & (blk[1:k + 1] != 0) & (blk[1:k + 1] != 0xffffffff)
            cand = np.nonzero(ok)[0]
            if not len(cand): continue
            v = blk[cand]; q = np.searchsorted(ks, v); q[q >= len(ks)] = 0
            sel = cand[ks[q] == v]
            for k, i, u in zip(sel.tolist(), blk[sel].tolist(), blk[sel + 1].tolist()):
                if u == i: continue
                b = m[al + 4 * (s + k) + 12]
                if tipos is None or b in tipos: out[i][(u, b) if tipos is None else u] += 1
    return {i: (c if tipos is None else c.most_common(1)[0][0]) for i, c in out.items()}
