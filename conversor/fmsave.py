#!/usr/bin/env python3
"""fmsave.py - lee el contenedor de partidas .fm de Football Manager (FM20 zlib / FM24 zstd).
Uso:
  fmsave.py list  partida.fm
  fmsave.py get   partida.fm nombre.ext salida.bin
  fmsave.py all   partida.fm carpeta_salida
Solo lectura: nunca modifica la partida."""
import sys, os, struct, zlib, subprocess, mmap

MAGIC = b'\x02\x01fmf.'
ZSTD = b'\x28\xb5\x2f\xfd'

def _unz(buf, comp):
    if comp == 'zlib':
        return zlib.decompress(buf)
    return subprocess.run(['zstd', '-d', '-c', '-q'], input=buf, stdout=subprocess.PIPE, check=True).stdout

class Save:
    def __init__(self, path):
        self.f = open(path, 'rb')
        self.m = mmap.mmap(self.f.fileno(), 0, access=mmap.ACCESS_READ)
        m = self.m
        if m[:6] != MAGIC: raise ValueError('no es un .fm')
        self.version = m[6]
        self.comp = {1: 'zlib', 3: 'zstd'}[m[25]]
        self.base = 26
        t = m.rfind(MAGIC)
        if t <= 0: raise ValueError('sin indice final')
        self.toc_off = t
        toc = _unz(m[t + 9:], self.comp)
        p = 0
        def s():
            nonlocal p
            n = struct.unpack_from('<I', toc, p)[0]; p += 4
            v = toc[p:p + n].decode('utf8', 'replace'); p += n
            return v
        self.name = s()
        cnt = struct.unpack_from('<I', toc, p)[0]; p += 4
        self.entries = []
        for _ in range(cnt):
            n = s(); e = s()
            off, c, r, t1, t2 = struct.unpack_from('<QQQqq', toc, p); p += 40
            self.entries.append(dict(name=n + e, off=off, comp=c, raw=r))
        self.toc_rest = toc[p:]
        self.sub = {}
        try:
            ns = struct.unpack_from('<I', toc, p)[0]; p += 4
            for _ in range(ns if ns < 16 else 0):
                g = s(); cnt = struct.unpack_from('<I', toc, p)[0]; p += 4; L = []
                for _ in range(cnt):
                    n = s(); e = s()
                    off, c, r, t1, t2 = struct.unpack_from('<QQQqq', toc, p); p += 40
                    L.append(dict(name=n + e, off=off, comp=c, raw=r))
                self.sub[g] = L
        except struct.error: self.sub = {}
    def read(self, name, grupo=None):
        for e in (self.entries if grupo is None else self.sub[grupo]):
            if e['name'] == name:
                a = self.base + e['off']
                d = _unz(self.m[a:a + e['comp']], self.comp)
                assert len(d) == e['raw'], (len(d), e['raw'])
                return d
        raise KeyError(name)

    def cache_path(self, name, cache=None):
        """path of the decompressed copy of an entry (created if missing), see read_mmap"""
        import os, hashlib
        cache = cache or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
        os.makedirs(cache, exist_ok=True)
        st = os.stat(self.f.name)
        key = hashlib.md5(('%s|%d|%d|%s' % (os.path.abspath(self.f.name), st.st_size, int(st.st_mtime), name)).encode()).hexdigest()
        p = os.path.join(cache, key + '.dat')
        if not os.path.exists(p):
            d = self.read(name); open(p + '.tmp', 'wb').write(d); del d; os.replace(p + '.tmp', p)
        return p
    def read_mmap(self, name, cache=None):
        """the entry decompressed once to a cache file and memory-mapped (read-only): a big game_db does not
        count against the memory of the process (the machine running the converter has ~3 GB)"""
        import os, hashlib
        cache = cache or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
        os.makedirs(cache, exist_ok=True)
        st = os.stat(self.f.name)
        key = hashlib.md5(('%s|%d|%d|%s' % (os.path.abspath(self.f.name), st.st_size, int(st.st_mtime), name)).encode()).hexdigest()
        p = os.path.join(cache, key + '.dat')
        if not os.path.exists(p):
            d = self.read(name); open(p + '.tmp', 'wb').write(d); del d; os.replace(p + '.tmp', p)
        fh = open(p, 'rb'); return mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)

if __name__ == '__main__':
    cmd, path = sys.argv[1], sys.argv[2]
    sv = Save(path)
    if cmd == 'list':
        print(f'# {sv.name}  version_contenedor={sv.version}  compresion={sv.comp}  entradas={len(sv.entries)}')
        for e in sv.entries: print(f"{e['raw']:>12} {e['comp']:>12} {e['off']:>12} {e['name']}")
    elif cmd == 'get':
        open(sys.argv[4], 'wb').write(sv.read(sys.argv[3]))
    elif cmd == 'all':
        os.makedirs(sys.argv[3], exist_ok=True)
        for e in sv.entries:
            open(os.path.join(sys.argv[3], e['name']), 'wb').write(sv.read(e['name']))
        print('extraidas', len(sv.entries))
