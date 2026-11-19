#!/usr/bin/env python3
"""convertir.py - conversor de partidas FM20 -> FM24 (EXPERIMENTAL). Solo necesita la partida de FM20 y una plantilla de FM24.
Uso:  convertir.py PASO partida_fm20.fm plantilla_fm24.fm salida.fm [carpeta_de_trabajo]
PASO: exportar20 | exportar24 | planificar | mundo | jugadores | relaciones | plazos | afiliados | clasificacion | manager | historial | carreras | temporada | todo
Cada paso deja sus resultados en la carpeta de trabajo; 'todo' los ejecuta en orden.
Nunca modifica la partida de FM20 ni la plantilla."""
import sys, os, subprocess, struct, csv, json, collections, datetime, mmap
AQUI = os.path.dirname(os.path.abspath(__file__))

def fecha_partida(path):
    """fecha de la partida: la primera fecha de save_game_summary.dat"""
    from fmsave import Save
    m = Save(path).read('save_game_summary.dat')
    for i in range(len(m) - 3):
        d, y = struct.unpack_from('<HH', m, i)
        if 1990 <= y <= 2100 and 1 <= (d & 0x1ff) <= 366:
            return datetime.date(y, 1, 1) + datetime.timedelta(days=(d & 0x1ff) - 1)

def py(*args, env=None):
    e = dict(os.environ); e.update(env or {})
    subprocess.run([sys.executable, *args], check=True, env=e, cwd=AQUI)

def leer_csv(path, cols):
    """rows of a CSV with only the given columns (a dict per row with every column takes gigabytes for 250k rows)"""
    r = csv.reader(open(path, encoding='utf-8-sig')); cab = next(r); ix = [cab.index(c) for c in cols]
    return [dict(zip(cols, (row[i] for i in ix))) for row in r]

def planificar(src, base, w):
    import fm_ligas as LG
    from fmsave import Save
    sm = Save(src).read('game_db.dat'); bm = Save(base).read('game_db.dat')
    ts = LG.team_zone(sm); tb = LG.team_zone(bm)
    import fm_uids as U, fm_equipos_club as EC   # clubs whose uid changed between FM20 and FM24
    tr = U.traduccion(sm, bm)[0]
    sec = EC.mapa_secundarios(sm, bm, ts, tb, tr)   # under-19 and other teams of a club, by their place in the club
    U.traducir_zona(ts, tr)
    u24 = {}
    for t, v in tb.items(): u24.setdefault(v['uid'], t)
    cols = ('id_jugador', 'id_club', 'id_club_contrato', 'pos_bloque', 'pos_nombre', 'POR', 'CA')   # only what is used: the CSVs of a long template are huge
    S = leer_csv(f'{w}/fm20.csv', cols); B = leer_csv(f'{w}/base.csv', cols)
    def ncont(x):
        c = int(x['pos_bloque']); o = int(x['pos_nombre']); key = struct.pack('<I', int(x['id_jugador']) + 1); k = c; n = 0
        while True:
            k = bm.find(key, k + 1, o)
            if k < 0: return n
            n += 1
    gk = lambda x: int(x['POR']) >= 15
    porB = collections.defaultdict(list)
    for x in B:
        if x['id_club']: porB[int(x['id_club'])].append(x)
    # cesiones: cada cesion de FM20 va sobre un cedido de FM24 (preferiblemente en el mismo club de destino)
    import fm_cedidos as CD
    destino0 = lambda t: u24.get(ts[t]['uid']) if t in ts else sec.get(t)
    import fm_plantillas as PL0
    conlista0 = {t for t, v in tb.items() if PL0.squad_of(bm, v)}
    huespedes = collections.defaultdict(list); todos_h = []
    for x in B:
        r = CD.cesion(bm, x, 8)
        if r and r[2] in conlista0 and r[3] in conlista0: huespedes[int(x['id_club'])].append(x); todos_h.append(x)
    usados_h = set(); ces = []; es_ces = set()
    for x in sorted(S, key=lambda x: -int(x['CA'])):
        r = CD.cesion(sm, x, 7)
        if not r: continue
        O, Lc = destino0(r[2]), destino0(r[3])
        if O is None or Lc is None or O not in conlista0 or Lc not in conlista0: continue
        h = next((y for y in huespedes[Lc] if y['id_jugador'] not in usados_h), None) or next((y for y in todos_h if y['id_jugador'] not in usados_h), None)
        if not h: break
        usados_h.add(h['id_jugador']); es_ces.add(x['id_jugador']); ces.append(f"{x['id_jugador']}:{h['id_jugador']}:{Lc}:{O}:1")
    open(f'{w}/cesiones_usadas.txt', 'w').write(' '.join(sorted(usados_h)))
    porS = collections.defaultdict(list)
    for x in S:
        if x['id_club'] and x['id_jugador'] not in es_ces: porS[int(x['id_club'])].append(x)
    destino = lambda t: u24.get(ts[t]['uid']) if t in ts else sec.get(t)
    pares = []; usados = set(); sobran = []; vistos = set()
    for t, pl in porS.items():
        d = destino(t)
        if d is None or d not in porB or d in vistos:
            continue
        vistos.add(d)
        # hosts: players of that team with one contract; B-team players have two records (contract with the parent
        # club + registration), accepted when the contract is with the club most of the team's players belong to
        cc = collections.Counter(x['id_club_contrato'] for x in porB[d]); padre = cc.most_common(1)[0][0] if cc else None
        if padre == str(d) or (padre and cc[padre] <= len(porB[d]) / 2): padre = None
        hh = [x for x in porB[d] if ncont(x) == 1 or (padre and x['id_club_contrato'] == padre and ncont(x) == 2)]
        sg = sorted([x for x in pl if gk(x)], key=lambda x: -int(x['CA'])); so = sorted([x for x in pl if not gk(x)], key=lambda x: -int(x['CA']))
        hg = sorted([x for x in hh if gk(x)], key=lambda x: -int(x['CA'])); ho = sorted([x for x in hh if not gk(x)], key=lambda x: -int(x['CA']))
        ng = min(len(sg), len(hg), 3); p = list(zip(sg[:ng], hg[:ng])) + list(zip(so, ho + hg[ng:]))
        pares += p; usados |= {h['id_jugador'] for _, h in p}
        u = {a['id_jugador'] for a, _ in p}; sobran += [(x, d) for x in pl if x['id_jugador'] not in u]
    # reciclables: jugadores de la plantilla sin usar en clubes convertidos, con un solo contrato de su propio club
    import fm_plantillas as PL
    conv = {d for _, d in sobran} | {int(h['id_club']) for _, h in pares}
    conlista = {t for t in conv if t in tb and PL.squad_of(bm, tb[t])}
    pool = [x for x in B if x['id_club'] and int(x['id_club']) in conlista and x['id_jugador'] not in usados and x['id_club'] == x['id_club_contrato'] and ncont(x) == 1]
    pg = [x for x in pool if gk(x)]; po = [x for x in pool if not gk(x)]
    trip = []
    for x, d in sorted(sobran, key=lambda z: -int(z[0]['CA'])):
        if d not in conlista: continue
        q = pg if gk(x) else po
        if q: trip.append(f"{x['id_jugador']}:{q.pop()['id_jugador']}:{d}")
    open(f'{w}/pares.txt', 'w').write(' '.join(f"{a['id_jugador']}:{h['id_jugador']}" for a, h in pares) + ' ' + ' '.join(trip) + ' ' + ' '.join(ces))
    conv_teams = {int(h['id_club']) for _, h in pares} | {int(t.split(':')[2]) for t in trip}
    open(f'{w}/equipos_convertidos.txt', 'w').write(' '.join(str(t) for t in sorted(conv_teams)))
    f20, f24 = fecha_partida(src), fecha_partida(base)
    anios = -round((f20 - f24).days / 365.25)
    json.dump(dict(fecha_fm20=str(f20), fecha_plantilla=str(f24), desplazar_anios=anios), open(f'{w}/desfase.json', 'w'))
    print(f'cesiones {len(ces)} | parejas {len(pares)} | reciclados {len(trip)} de {len(sobran)} sin hueco | equipos convertidos {len(conv_teams)} | fechas FM20 {f20} plantilla {f24} -> desplazar {anios} anios')

def main():
    paso, src, base, out = sys.argv[1], *map(os.path.abspath, sys.argv[2:5])
    w = os.path.abspath(sys.argv[5] if len(sys.argv) > 5 else 'trabajo'); os.makedirs(w, exist_ok=True)
    pasos = ['exportar20', 'exportar24', 'planificar', 'mundo', 'jugadores', 'relaciones', 'plazos', 'afiliados', 'clasificacion', 'manager', 'historial', 'carreras', 'temporada'] if paso == 'todo' else [paso]
    sal_jug = f'{w}/jugadores.fm' if 'historial' in pasos else out
    sal_his = f'{w}/historial.fm' if 'temporada' in pasos else out
    for p in pasos:
        print('==', p, flush=True)
        if p == 'exportar20': py('fm_export.py', src, f'{w}/fm20.csv')
        elif p == 'exportar24': py('fm_export.py', base, f'{w}/base.csv')
        elif p == 'planificar': planificar(src, base, w)
        elif p == 'mundo':
            py('fm_mundo.py', src, base, f'{w}/mundo.fm', env=dict(CSV20=f'{w}/fm20.csv', CSV24=f'{w}/base.csv', CESIONES_EQUIPOS=f'{w}/equipos_convertidos.txt', CESIONES_EXCLUIR=f'{w}/cesiones_usadas.txt'))
        elif p == 'jugadores':
            des = json.load(open(f'{w}/desfase.json'))
            py('fm_trasplante.py', src, f'{w}/mundo.fm', sal_jug, '@' + f'{w}/pares.txt', env=dict(ECONOMIA='1', DESPLAZAR_ANIOS=str(des['desplazar_anios']), HISTORIAL_JUGADORES=f'{w}/historial_jugadores.json'))
        elif p == 'relaciones':   # rewrites jugadores.fm in place (through a temporary file)
            py('fm_relaciones.py', src, f'{w}/jugadores.fm', f'{w}/relaciones.tmp.fm', f'{w}/pares.txt')
            os.replace(f'{w}/relaciones.tmp.fm', f'{w}/jugadores.fm')
        elif p == 'plazos':   # transfer installments (transfer_man.dat), rewrites jugadores.fm in place
            des = json.load(open(f'{w}/desfase.json'))
            py('fm_plazos.py', src, f'{w}/jugadores.fm', f'{w}/plazos.tmp.fm', f'{w}/pares.txt', str(des['desplazar_anios']))
            os.replace(f'{w}/plazos.tmp.fm', f'{w}/jugadores.fm')
        elif p == 'afiliados':   # club affiliations (game_db.dat), rewrites jugadores.fm in place
            des = json.load(open(f'{w}/desfase.json'))
            py('fm_afiliados.py', src, f'{w}/jugadores.fm', f'{w}/afiliados.tmp.fm', str(des['desplazar_anios']))
            os.replace(f'{w}/afiliados.tmp.fm', f'{w}/jugadores.fm')
        elif p == 'clasificacion':   # final league tables in the FM20 order (fm_clasificacion.py), rewrites jugadores.fm
            py('fm_clasificacion.py', src, f'{w}/jugadores.fm', f'{w}/clasificacion.tmp.fm')
            os.replace(f'{w}/clasificacion.tmp.fm', f'{w}/jugadores.fm')
        elif p == 'manager':   # the human manager (fm_manager.py), rewrites jugadores.fm in place
            des = json.load(open(f'{w}/desfase.json'))
            py('fm_manager.py', src, f'{w}/jugadores.fm', f'{w}/manager.tmp.fm', str(des['desplazar_anios']))
            os.replace(f'{w}/manager.tmp.fm', f'{w}/jugadores.fm')
        elif p == 'historial':
            des = json.load(open(f'{w}/desfase.json'))
            py('fm_hist_liga.py', src, base, f'{w}/jugadores.fm', sal_his, str(des['desplazar_anios']), env=dict(TRABAJO=w, HISTORIAL_PARTE='liga'))
        elif p == 'carreras':   # player career history and injuries (separate process: memory), rewrites historial.fm
            des = json.load(open(f'{w}/desfase.json'))
            py('fm_hist_liga.py', src, base, f'{w}/historial.fm', f'{w}/carreras.tmp.fm', str(des['desplazar_anios']), env=dict(TRABAJO=w, HISTORIAL_PARTE='jugadores'))
            os.replace(f'{w}/carreras.tmp.fm', f'{w}/historial.fm')
        elif p == 'temporada':
            des = json.load(open(f'{w}/desfase.json'))
            py('fm_hist_temporada.py', src, base, f'{w}/historial.fm', out, str(des['desplazar_anios']), env=dict(TRABAJO=w))

if __name__ == '__main__':
    main()
