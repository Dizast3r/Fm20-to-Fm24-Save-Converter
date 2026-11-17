"""historial de liga de cada equipo (tc_league_history): filas de 24 bytes en _dt, listas de offsets en _ls (ver fm_tad).
fila: [año u16 (fin de temporada)][competicion u16][posicion u8 (0 = campeon)][equipos u8][fase u8][..][ffffffff][estadisticas 12]
Los bloques no dicen de que equipo son: van en orden de numero de equipo (solo equipos con historial)."""
import fm_tad as T
def leer(ls, dt):
    L, cab, cola, d0 = T.leer(ls)
    return [[bytes(dt[d0 + o:d0 + o + 24]) for o in l] for l in L], cab, cola, dt[:d0]
def offsets(ls): return T.leer(ls)[0]
def leer24(ls, dt): return leer(ls, dt)[0]
cab = T.cab
