#!/usr/bin/env python3
"""
move_skipped.py

Przenosi z pliku części (eng_rus_*.json) do eng_pol.json wpisy, w których
pole `eng` i `rus` są identyczne (czyli nic nie zostało przetłumaczone).

- Usuwa takie wpisy z pliku części.
- Dodaje je do eng_pol.json, zamieniając klucz `rus` na `pol`.
- Zachowuje inne pola (jeśli jakieś są).
- Tworzy pliki .bak przed nadpisaniem (chyba że --no-backup).
"""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path


def resolve_json_path(value: str) -> Path:
    """Pozwala podać nazwę pliku z rozszerzeniem .json lub bez."""
    path = Path(value)
    if path.is_file():
        return path
    if not path.suffix:
        candidate = path.with_suffix(".json")
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"Nie znaleziono pliku JSON: {value}")


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data, backup: bool = True):
    if backup and path.exists():
        backup_path = path.with_name(path.name + ".bak")
        shutil.copy2(path, backup_path)
        print(f"[backup] {backup_path}")

    tmp_path = path.with_name(path.name + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp_path, path)
    print(f"[zapis]  {path}")


def is_untranslated(entry: dict) -> bool:
    """True, gdy eng i rus są identyczne (nic nie zostało przetłumaczone)."""
    if not isinstance(entry, dict):
        return False
    eng = entry.get("eng")
    rus = entry.get("rus")
    if eng is None or rus is None:
        return False
    return eng == rus


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Przenosi z pliku części do eng_pol.json wpisy, w których eng == rus "
            "(nietłumaczone). Klucz 'rus' zostaje zamieniony na 'pol'."
        )
    )
    parser.add_argument(
        "part",
        help="Plik części, np. eng_rus_part1_part1 lub eng_rus_part1_part1.json",
    )
    parser.add_argument(
        "-r", "--reference",
        default=None,
        help="Ścieżka do eng_pol.json. Domyślnie eng_pol.json obok pliku części.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Tylko pokaż, co zostałoby przeniesione; nie zapisuj zmian.",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Nie twórz plików .bak.",
    )
    parser.add_argument(
        "--include-empty",
        action="store_true",
        help="Przenoś także wpisy, w których eng i rus są puste (domyślnie pomijane).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Nadpisz istniejące wpisy w eng_pol.json (domyślnie pomijane z ostrzeżeniem).",
    )
    parser.add_argument(
        "--show",
        type=int,
        default=10,
        help="Ile przykładowych kluczy pokazać (domyślnie 10).",
    )

    args = parser.parse_args()

    part_path = resolve_json_path(args.part)
    ref_path = (
        resolve_json_path(args.reference)
        if args.reference
        else part_path.with_name("eng_pol.json")
    )

    if not ref_path.is_file():
        print(f"Błąd: nie znaleziono pliku eng_pol: {ref_path}", file=sys.stderr)
        sys.exit(1)

    part_data = load_json(part_path)
    pol_data = load_json(ref_path)

    to_move = []
    skipped_empty = 0

    for key, entry in part_data.items():
        if not is_untranslated(entry):
            continue
        # Opcjonalnie pomiń puste
        if not args.include_empty and entry.get("eng", "") == "" and entry.get("rus", "") == "":
            skipped_empty += 1
            continue
        to_move.append(key)

    print(f"Plik części:  {part_path}")
    print(f"Plik eng_pol: {ref_path}")
    print(f"Wpisów z eng == rus: {len(to_move)}"
          + (f" (+{skipped_empty} pominiętych pustych)" if skipped_empty else ""))

    if not to_move:
        print("Nic do przeniesienia.")
        return

    # Przenieś
    already_in_pol = []
    moved = 0

    for key in to_move:
        entry = part_data[key]

        # Buduj wpis do eng_pol
        new_entry = dict(entry)
        if "rus" in new_entry:
            new_entry["pol"] = new_entry.pop("rus")

        if key in pol_data and not args.overwrite:
            already_in_pol.append(key)
            continue

        # Dodaj / nadpisz w eng_pol
        pol_data[key] = new_entry

        # Usuń z części
        del part_data[key]
        moved += 1

    print(f"Przeniesiono: {moved}")
    if already_in_pol:
        print(f"Pominięto (już istnieje w eng_pol, użyj --overwrite): {len(already_in_pol)}")

    # Podgląd
    shown = [k for k in to_move if k not in already_in_pol][:args.show]
    if shown:
        print("Przykłady przeniesionych kluczy:")
        for k in shown:
            print(f"  - {k}")

    if args.dry_run:
        print("DRY-RUN: nic nie zapisano.")
        return

    if moved == 0 and not already_in_pol:
        print("Nic do zapisania.")
        return

    # Zapisz tylko jeśli faktycznie coś zmieniliśmy
    if moved > 0:
        save_json(part_path, part_data, backup=not args.no_backup)
        save_json(ref_path, pol_data, backup=not args.no_backup)


if __name__ == "__main__":
    main()