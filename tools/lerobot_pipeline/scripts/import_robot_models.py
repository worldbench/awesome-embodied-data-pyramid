"""Import explicitly supplied FK models after verifying their content hashes."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]

def verify(path, row):
    return path.is_file() and path.stat().st_size == row['bytes'] and hashlib.sha256(path.read_bytes()).hexdigest() == row['sha256']

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--source', type=Path)
    group.add_argument('--check', action='store_true')
    args = parser.parse_args()
    destination = ROOT / 'quality/robot_models'
    source = args.source.resolve() if args.source else destination
    rows = json.loads((ROOT / 'configs/robot-models.manifest.json').read_text())['files']
    for row in rows:
        relative = Path(row['path'])
        if relative.is_absolute() or '..' in relative.parts:
            raise SystemExit('Unsafe model manifest path')
        if not verify(source / relative, row):
            raise SystemExit(f'Missing or mismatched model: {relative}')
        target = destination / relative
        if target.exists() and not verify(target, row):
            raise SystemExit(f'Refusing to replace different model: {relative}')
    if not args.check:
        for row in rows:
            relative = Path(row['path']); target = destination / relative
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source / relative, target)
                if not verify(target, row):
                    raise SystemExit(f'Imported file failed verification: {relative}')
    print(f'Verified {len(rows)} model resource files.')

if __name__ == '__main__':
    main()
