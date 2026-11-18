"""International caps: [caps u8][goals u8][youth caps u8][youth goals u8][date][date] inside the person record,
after the injury field (fm_lesiones.campo) and right before the field [u8][flag]([u32] if flag)[u32][05 00]
(the milestones list, fm_lesiones.campo_hitos). Same layout in FM20 and FM24.
Example FM24 template (June 2023): Cristiano Ronaldo c8 7b 0a 03 = 200 caps, 123 goals, 10 U21 caps, 3 U21 goals;
Messi 175 / 103 / 18 / 14."""
import re, struct
PAT = re.compile(rb'(.{4})(..[\x6c-\xff]\x07)(..[\x6c-\xff]\x07).(?:\x00|\x01.{4}).{4}\x05\x00', re.S)
def campo(m, q, limite=400):
    """position of the 4 caps bytes; q = position of the injury field of the same record"""
    x = PAT.search(m, q + 4, q + limite)
    return x.start(1) if x else None
def buscar(m, pb, pn, lesion=None):
    """caps position of the record that goes from pb (attribute block) to pn (name record); lesion = injury field"""
    if lesion: return campo(m, lesion)
    x = PAT.search(m, min(pb, pn), max(pb, pn))
    return x.start(1) if x else None
# International debut and first goal: 01 00 6c 07 00 [debut date][nation u32][first goal date][nation u32], a few hundred
# bytes before the caps field (FM20 and FM24; e.g. Mbappe FM20: 2017 day 84 v 154 Luxembourg, day 243 v 158 Netherlands)
DEBUT = re.compile(rb'\x01\x00\x6c\x07\x00(..[\x6c-\xff]\x07)(.{4})(..[\x6c-\xff]\x07)(.{4})', re.S)
def debut(m, caps, ventana=1500):
    """position of the debut date (the last match before the caps field), or None"""
    q = None
    for x in DEBUT.finditer(m, max(0, caps - ventana), caps): q = x.start(1)
    return q
