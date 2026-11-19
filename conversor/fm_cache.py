"""Results of slow scans of a game_db kept on disk (cache/), keyed by the save files and the function: the steps of a
long template have 3 minutes each, and the same maps (team / stadium / club unique ids) are needed by several steps."""
import os, pickle, hashlib
DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
def clave(nombre, *rutas):
    h = hashlib.md5(nombre.encode())
    for r in rutas:
        st = os.stat(r); h.update(('%s|%d|%d' % (os.path.abspath(r), st.st_size, int(st.st_mtime))).encode())
    return os.path.join(DIR, 'res_' + h.hexdigest() + '.pkl')
def memo(nombre, rutas, f):
    os.makedirs(DIR, exist_ok=True); p = clave(nombre, *rutas)
    if os.path.exists(p):
        try: return pickle.load(open(p, 'rb'))
        except Exception: pass
    r = f(); pickle.dump(r, open(p + '.tmp', 'wb')); os.replace(p + '.tmp', p); return r
