#!/usr/bin/env python3
"""Podziel eng_rus.json na N równych części (po ~3-4 MB każda)."""
import json, math, os

SRC = 'eng_rus.json'
N = 2                      # 16 MB / 5 ≈ 3.2 MB na część
OUT = 'eng_rus_part'       # -> eng_rus_part1.json ... eng_rus_part5.json

with open(SRC, encoding='utf-8') as f:
    data = json.load(f)

# usuń Invalid jeśli jest (nie tłumaczymy)
data.pop('Invalid', None)

items = list(data.items())
chunk = math.ceil(len(items) / N)

for i in range(N):
    part = dict(items[i*chunk:(i+1)*chunk])
    if not part:
        continue
    path = f'{OUT}{i+1}.json'
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(part, f, ensure_ascii=False, indent=1)
    print(f'{path}: {len(part)} wpisów, {os.path.getsize(path)/1024:.0f} KB')

print(f'\nRazem: {len(items)} wpisów w {N} częściach')