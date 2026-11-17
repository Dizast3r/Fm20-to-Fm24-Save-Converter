"""cesiones: jugadores con contrato de su club dueno + contrato de cesion (byte de tipo = 1)"""
import struct
def contratos(m, x):
    c = int(x['pos_bloque']); o = int(x['pos_nombre']); key = struct.pack('<I', int(x['id_jugador']) + 1); k = c; out = []
    while True:
        k = m.find(key, k + 1, o)
        if k < 0: return out
        out.append(k)
def cesion(m, x, ver):
    """(contrato_dueno, contrato_cesion, club_dueno, club_cesion) o None"""
    if not x['id_club']: return None
    kk = contratos(m, x)
    if len(kk) < 2: return None
    tipo = m[kk[0] + (14 if ver == 7 else 19)]
    if tipo != 1: return None
    cur = int(x['id_club']); dueno = struct.unpack_from('<I', m, kk[0] + 4)[0]
    if dueno == cur: return None
    ces = [k for k in kk[1:] if struct.unpack_from('<I', m, k + 4)[0] == cur]
    if not ces: return None
    if ver == 8 and len(kk) != 2: return None
    return kk[0], ces[-1], dueno, cur
