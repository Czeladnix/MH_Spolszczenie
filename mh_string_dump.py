#!/usr/bin/env python3
"""Eksport .string (Marvel Heroes, klient 1.52) do CSV. Format odtworzony metodą
prób i błędów - NIE jest oficjalnie udokumentowany. Użycie: python mh_string_dump.py plik.string [out.csv]"""
import struct, sys, csv
def parse(path):
    d = open(path, 'rb').read()
    if d[:4] != b'STR\x02':
        raise SystemExit('To nie wygląda na plik STR\\x02')
    first_off = struct.unpack_from('<I', d, 18)[0]
    n = (first_off - 18) // 16
    rows = []
    for i in range(n):
        off, sid, cnt, flag = struct.unpack_from('<IQHH', d, 18 + 16 * i)
        end = d.find(b'\0', off)
        txt = d[off:end].decode('utf-8', 'replace') if end != -1 else ''
        rows.append((i, f'{sid:016X}', cnt, f'{flag:04X}', txt))
    return n, rows
if __name__ == '__main__':
    n, rows = parse(sys.argv[1])
    out = sys.argv[2] if len(sys.argv) > 2 else sys.argv[1] + '.csv'
    with open(out, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f); w.writerow(['idx', 'id', 'cnt', 'flag', 'text']); w.writerows(rows)
    print(n, 'rekordów ->', out)
