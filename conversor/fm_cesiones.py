"""cesiones: el ultimo contrato de un jugador cedido es el de la cesion; su fecha de fin va tras ff*8, seguida de la de inicio"""
import struct, datetime
def okd(m, p):
    d, y = struct.unpack_from('<HH', m, p); return 2000 <= y <= 2060 and 1 <= (d & 0x1ff) <= 366
def loan_dates(m, k):
    for q in range(k - 30, k - 200, -1):
        if m[q:q + 8] == b'\xff' * 8 and okd(m, q + 8) and okd(m, q + 12): return q + 8, q + 12
    return None
def todate(m, p):
    d, y = struct.unpack_from('<HH', m, p); return datetime.date(y, 1, 1) + datetime.timedelta(days=(d & 0x1ff) - 1)
