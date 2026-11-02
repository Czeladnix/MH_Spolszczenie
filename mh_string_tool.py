#!/usr/bin/env python3
"""Konwerter .string (Marvel Heroes, klient 1.52, format STR v2) <-> JSON.
Format odtworzony przez porównanie z plikami JSON z repozytorium rosyjskiego spolszczenia.
  python mh_string_tool.py unpack  plik.string  plik.json
  python mh_string_tool.py pack    plik.json    plik.string
  python mh_string_tool.py verify  plik.string            # unpack -> pack -> porównanie bajtów
JSON: {"Magic":"STR","Version":2,"EntryCount":N,"StringMap":{id:{"Variants":[...],"FlagsProduced":n,"String":"..."}}}
"""
import struct, json, sys

def unpack(data):
    assert data[:3] == b'STR', 'brak nagłówka STR'
    ver = data[3]
    count = struct.unpack_from('<H', data, 4)[0]
    pos = 6
    def s(off):
        return data[off:data.index(b'\0', off)].decode('utf-8')
    sm = {}
    for _ in range(count):
        sid, n, fp, off = struct.unpack_from('<QHHI', data, pos); pos += 16
        e = {'Variants': [], 'FlagsProduced': fp, 'String': s(off)}
        for _ in range(n - 1):
            fc, vfp, voff = struct.unpack_from('<QHI', data, pos); pos += 14
            e['Variants'].append({'FlagsConsumed': fc, 'FlagsProduced': vfp, 'String': s(voff)})
        sm['Invalid' if sid == 0 else str(sid)] = e
    return {'Magic': 'STR', 'Version': ver, 'EntryCount': count, 'StringMap': sm}

def pack(obj):
    sm = obj['StringMap']
    entries = list(sm.items())
    # rozmiar tabeli rekordów
    table_size = 6 + sum(16 + 14 * len(e['Variants']) for _, e in entries)
    table = bytearray(b'STR' + bytes([obj.get('Version', 2)]) + struct.pack('<H', len(entries)))
    pool = bytearray()
    def add(text):
        off = table_size + len(pool)
        pool.extend(text.encode('utf-8') + b'\0')
        return off
    for k, e in entries:
        sid = 0 if k == 'Invalid' else int(k)
        v = e['Variants']
        table += struct.pack('<QHHI', sid, len(v) + 1, e['FlagsProduced'], add(e['String']))
        for x in v:
            table += struct.pack('<QHI', x['FlagsConsumed'], x['FlagsProduced'], add(x['String']))
    return bytes(table + pool)

if __name__ == '__main__':
    if len(sys.argv) < 3: sys.exit(__doc__)
    cmd, a = sys.argv[1], sys.argv[2]
    if cmd == 'unpack':
        o = unpack(open(a, 'rb').read())
        json.dump(o, open(sys.argv[3], 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        print(o['EntryCount'], 'wpisów ->', sys.argv[3])
    elif cmd == 'pack':
        o = json.load(open(a, encoding='utf-8'))
        open(sys.argv[3], 'wb').write(pack(o)); print('zapisano', sys.argv[3])
    elif cmd == 'verify':
        orig = open(a, 'rb').read()
        new = pack(unpack(orig))
        print('identyczne bajt w bajt' if new == orig else f'RÓŻNICA (orig {len(orig)} B, nowy {len(new)} B)')
