"""fmcontenedor.py - lee y RECONSTRUYE el contenedor .fm (FM24, zstd) con ficheros internos de cualquier tamano.
Estructura: cabecera 26 bytes [02 01 'fmf.'][ver][00 00][u64 = pos_indice-9][9 bytes][compresion]
            datos de cada fichero (comprimidos) en base 26 + off
            indice: [02 01 'fmf.'][ver][00 00][zstd(indice)]
            indice: [nombre][n][n x (nombre, ext, off u64, comp u64, raw u64, t1, t2)][n_sub][por subdirectorio: nombre, n, entradas]"""
import struct, subprocess
MAGIC = b'\x02\x01fmf.'
def unz(b): return subprocess.run(['zstd', '-d', '-c', '-q'], input=b, stdout=subprocess.PIPE, check=True).stdout
def z(b, lvl='-9'): return subprocess.run(['zstd', '-T0', lvl, '-c', '-q'], input=b, stdout=subprocess.PIPE, check=True).stdout

class Contenedor:
    def __init__(self, path):
        self.path = path
        self.data = open(path, 'rb').read()
        d = self.data
        assert d[:6] == MAGIC and d[25] == 3, 'solo FM24 (zstd)'
        self.hdr = bytearray(d[:26])
        t = struct.unpack_from('<Q', d, 9)[0] + 9
        assert d[t:t + 6] == MAGIC
        self.toc_hdr = d[t:t + 9]
        toc = unz(d[t + 9:])
        p = 0
        def s():
            nonlocal p
            n = struct.unpack_from('<I', toc, p)[0]; p += 4; v = toc[p:p + n]; p += n; return v
        self.nombre = s()
        self.entries = []          # (grupo, nombre, ext, off, comp, raw, t1, t2)
        for _ in range(struct.unpack_from('<I', toc, p)[0] if True else 0):
            pass
        n = struct.unpack_from('<I', toc, p)[0]; p += 4
        for _ in range(n):
            a = s(); e = s(); off, c, r, t1, t2 = struct.unpack_from('<QQQqq', toc, p); p += 40
            self.entries.append(['', a, e, off, c, r, t1, t2])
        self.subs = []
        ns = struct.unpack_from('<I', toc, p)[0]; p += 4
        for _ in range(ns):
            sn = s(); n = struct.unpack_from('<I', toc, p)[0]; p += 4; self.subs.append((sn, n))
            for _ in range(n):
                a = s(); e = s(); off, c, r, t1, t2 = struct.unpack_from('<QQQqq', toc, p); p += 40
                self.entries.append([sn, a, e, off, c, r, t1, t2])
        self.toc_tail = toc[p:]
        self.toc_len = len(toc)
    def names(self): return [(g, (a + e).decode('utf8', 'replace')) for g, a, e, *_ in self.entries]
    def _find(self, name, grupo=None):
        for x in self.entries:
            if (x[1] + x[2]).decode('utf8', 'replace') == name and (grupo is None or x[0] == (grupo.encode() if isinstance(grupo, str) else grupo)): return x
        raise KeyError(name)
    def read(self, name, grupo=None):
        x = self._find(name, grupo); a = 26 + x[3]; d = unz(self.data[a:a + x[4]]); assert len(d) == x[5]; return d
    def cobertura(self):
        """comprueba que los datos de los ficheros cubren todo el archivo entre la cabecera y el indice"""
        iv = sorted((26 + x[3], 26 + x[3] + x[4]) for x in self.entries)
        t = struct.unpack_from('<Q', self.data, 9)[0] + 9
        huecos = []; cur = 26
        for a, b in iv:
            if a != cur: huecos.append((cur, a))
            cur = max(cur, b)
        if cur != t: huecos.append((cur, t))
        return huecos
    def escribir(self, out, nuevos=None, lvl='-9'):
        """nuevos: {(grupo, nombre): bytes sin comprimir}. Conserva el orden fisico original."""
        nuevos = nuevos or {}
        orden = sorted(range(len(self.entries)), key=lambda i: self.entries[i][3])
        blobs = {}; pos = 0; newoff = {}
        for i in orden:
            g, a, e, off, c, r, t1, t2 = self.entries[i]
            k = (g.decode() if isinstance(g, bytes) else g, (a + e).decode('utf8', 'replace'))
            if k in nuevos: raw = nuevos[k]; blob = z(raw, lvl if len(raw) < (64 << 20) else '-3'); rawlen = len(raw)
            else: blob = self.data[26 + off:26 + off + c]; rawlen = r
            blobs[i] = (blob, rawlen); newoff[i] = pos; pos += len(blob)
        def ps(b): return struct.pack('<I', len(b)) + b
        toc = bytearray(ps(self.nombre))
        main = [i for i, x in enumerate(self.entries) if x[0] == '']
        toc += struct.pack('<I', len(main))
        for i in main:
            g, a, e, off, c, r, t1, t2 = self.entries[i]
            toc += ps(a) + ps(e) + struct.pack('<QQQqq', newoff[i], len(blobs[i][0]), blobs[i][1], t1, t2)
        toc += struct.pack('<I', len(self.subs))
        k = len(main)
        for sn, n in self.subs:
            toc += ps(sn) + struct.pack('<I', n)
            for i in range(k, k + n):
                g, a, e, off, c, r, t1, t2 = self.entries[i]
                toc += ps(a) + ps(e) + struct.pack('<QQQqq', newoff[i], len(blobs[i][0]), blobs[i][1], t1, t2)
            k += n
        toc += self.toc_tail
        hdr = bytearray(self.hdr); struct.pack_into('<Q', hdr, 9, 26 + pos - 9)
        with open(out, 'wb') as f:
            f.write(hdr)
            for i in orden: f.write(blobs[i][0])
            f.write(self.toc_hdr); f.write(z(bytes(toc), '-19'))
        return pos
