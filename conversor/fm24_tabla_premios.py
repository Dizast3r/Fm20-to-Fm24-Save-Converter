#!/usr/bin/env python3
"""Builds data/fm24_awards.json: how each FM24 award id is used in milestone rows -> [type, flag, competition, rows].
Award ids belong to the game database, so any FM24 save with a long career gives the same table; the template rarely
has enough rows (no team of the week before the first match). Usage: fm24_tabla_premios.py person_record_history_ls.dat
person_record_history_dt.cmt [out.json]   (both files extracted from an FM24 save)"""
import sys, json, struct, collections
import fm_tad as T
def uso(ls, dt, R):
    """{award: Counter((type, flag, comp))} from milestone rows (R = 44 FM20, 42 FM24)"""
    L, _, _, a0 = T.leer(ls); c = collections.defaultdict(collections.Counter)
    for l in L:
        for o in l:
            r = dt[a0 + o:a0 + o + R]
            if R == 44:
                aw, comp = struct.unpack_from('<H', r, 16)[0], struct.unpack_from('<H', r, 14)[0]; ty, fl = r[42], r[43]
                if aw == 0xffff: continue
            else:
                if r[37] == 0 and r[38:42] == b'\xff\xff\xff\xff': continue
                aw, comp = struct.unpack_from('<H', r, 37)[0], struct.unpack_from('<H', r, 35)[0]; ty, fl = r[24], r[25]
            c[aw][(ty, fl, comp)] += 1
    return c
if __name__ == '__main__':
    a = sys.argv[1:]
    c = uso(open(a[0], 'rb').read(), open(a[1], 'rb').read(), 42)
    out = {str(aw): list(v.most_common(1)[0][0]) + [sum(v.values())] for aw, v in sorted(c.items())}
    json.dump(out, open(a[2] if len(a) > 2 else 'data/fm24_awards.json', 'w'), separators=(',', ':'))
    print(len(out), 'awards')
