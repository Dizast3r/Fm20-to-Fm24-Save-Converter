"""Last finished season(s) of every competition: the database (game_db.dat) keeps the rows of the latest season(s)
(winner, runner-up, final venue...) until the next season starts; they are not in comp_history yet.
Overwrites, in place, the rows of the FM24 game_db with the FM20 ones (same competitions as comp_history).
usage: fm_hist_temporada.py fm20.fm template24.fm input24.fm output.fm years_offset   (env TRABAJO = work folder,
       it needs hist_mapas.pkl written by fm_hist_liga.py)"""
import sys, os, pickle, mmap, tempfile
import fmsave, fmcontenedor as C, fm_hist_comp as HC
def main(src20, plantilla, entrada, salida, desp):
    W = os.environ.get('TRABAJO', 'trabajo'); M = pickle.load(open(W + '/hist_mapas.pkl', 'rb'))
    s20 = fmsave.Save(src20); P = C.Contenedor(plantilla); E = C.Contenedor(entrada)
    fd, p = tempfile.mkstemp(); os.write(fd, s20.read('game_db.dat')); os.close(fd)
    f = open(p, 'rb'); m20 = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    gdb = bytearray(E.read('game_db.dat'))
    est = HC.transferir_db(gdb, m20, s20.read('comp_history_ls.dat', 'rgman'), s20.read('comp_history_dt.cmt'),
                           P.read('comp_history_ls.dat', 'rgman'), P.read('comp_history_dt.cmt'), M['cpar'],
                           M['tu20'], M['tu24'], M['es20'], M['es24'], desp)
    m20.close(); f.close(); os.unlink(p)
    E.escribir(salida, {('', 'game_db.dat'): bytes(gdb)})
    print('ultima temporada (base de datos): ' + ' | '.join('%s %d' % kv for kv in est.items()))
if __name__ == '__main__':
    a = sys.argv[1:]; main(a[0], a[1], a[2], a[3], int(a[4]))
