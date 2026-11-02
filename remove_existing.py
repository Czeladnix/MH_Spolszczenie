#!/usr/bin/env python3
import argparse
import json
import os
import shutil
from pathlib import Path


def resolve_json_path(value: str) -> Path:
    """Pozwala podać nazwę z .json lub bez."""
    path = Path(value)
    if path.is_file():
        return path

    if not path.suffix:
        path_with_json = path.with_suffix(".json")
        if path_with_json.is_file():
            return path_with_json

    raise FileNotFoundError(f"Nie znaleziono pliku JSON: {value}")


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(
        description="Usuwa z pliku eng_rus_partX wpisy, których ID występują już w eng_pol.json."
    )
    parser.add_argument(
        "part",
        help="Plik części, np. eng_rus_part1_part1 lub eng_rus_part1_part1.json",
    )
    parser.add_argument(
        "-r",
        "--reference",
        default=None,
        help="Plik referencyjny. Domyślnie eng_pol.json w katalogu pliku części.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Plik wynikowy. Domyślnie nadpisuje plik wejściowy.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Tylko pokaż, ile wpisów zostałoby usuniętych; nie zapisuj zmian.",
    )
    parser.add_argument(
        "--skip-skipped",
        action="store_true",
        help="Nie usuwaj wpisów, które w eng_pol mają skipped=true.",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Nie twórz kopii .bak przy nadpisywaniu pliku wejściowego.",
    )

    args = parser.parse_args()

    part_path = resolve_json_path(args.part)

    if args.reference:
        ref_path = resolve_json_path(args.reference)
    else:
        ref_path = part_path.with_name("eng_pol.json")

    if not ref_path.is_file():
        raise FileNotFoundError(f"Nie znaleziono pliku referencyjnego: {ref_path}")

    data = load_json(part_path)
    reference = load_json(ref_path)

    if args.skip_skipped:
        reference_keys = {
            key
            for key, value in reference.items()
            if not (isinstance(value, dict) and value.get("skipped") is True)
        }
    else:
        reference_keys = set(reference.keys())

    before_count = len(data)
    removed_keys = [key for key in data.keys() if key in reference_keys]

    for key in removed_keys:
        data.pop(key, None)

    after_count = len(data)

    output_path = Path(args.output) if args.output else part_path

    print(f"Plik wejściowy: {part_path}")
    print(f"Plik referencyjny: {ref_path}")
    print(f"Usunięto wpisów: {len(removed_keys)}")
    print(f"Przed: {before_count}, po: {after_count}")

    if removed_keys:
        print("Przykładowe usunięte ID:")
        for key in removed_keys[:10]:
            print(f"  - {key}")

    if args.dry_run:
        print("DRY-RUN: nie zapisano żadnych zmian.")
        return

    # Backup tylko wtedy, gdy nadpisujemy plik wejściowy.
    if output_path.resolve() == part_path.resolve() and not args.no_backup:
        backup_path = part_path.with_name(part_path.name + ".bak")
        shutil.copy2(part_path, backup_path)
        print(f"Utworzono backup: {backup_path}")

    tmp_path = output_path.with_name(output_path.name + ".tmp")

    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    os.replace(tmp_path, output_path)
    print(f"Zapisano: {output_path}")


if __name__ == "__main__":
    main()