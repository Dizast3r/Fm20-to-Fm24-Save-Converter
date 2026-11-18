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
