"""Read split tar.gz archives sequentially without concatenating/extracting them all."""
import csv
import io
import os
import re
from pathlib import Path

SUPPORTED = {'franka_1rgb', 'franka_3rgb', 'franka_fr3_dual',
             'tienkung_gello_1rgb', 'tienkung_prod1_gello_1rgb', 'tienkung_xsens_1rgb', 'ur_1rgb'}


class PartsReader(io.RawIOBase):
    def __init__(self, paths):
        self.paths = iter(paths)
        self.stream = None
        self.bytes_read = 0

    def readable(self):
        return True

    def readinto(self, buffer):
        while True:
            if self.stream is None:
                path = next(self.paths, None)
                if path is None:
                    return 0
                self.stream = open(path, 'rb', buffering=0)
            count = self.stream.readinto(buffer)
            if count:
                self.bytes_read += count
                return count
            self.stream.close()
            self.stream = None

    def close(self):
        if self.stream is not None:
            self.stream.close()
        super().close()


def inventory(root):
    root = Path(root)
    with (root / 'static/RoboMIND_v1_2_instr.csv').open(newline='') as f:
        instructions = {r['task']: r['instruction'] for r in csv.DictReader(f)}
    archives, excluded, missing = [], [], []
    for benchmark in sorted(root.glob('benchmark*_compressed')):
        for embodiment in sorted(benchmark.iterdir()):
            if not embodiment.is_dir():
                continue
            kind = embodiment.name.removeprefix('h5_')
            groups = {}
            for entry in os.scandir(embodiment):
                if not entry.is_file() or not re.search(r'\.tar\.gz(?:\.part-[a-z]+)?$', entry.name):
                    continue
                task = entry.name.split('.tar.gz')[0]
                groups.setdefault(task, []).append({'path': entry.path, 'size': entry.stat().st_size})
            for task, files in sorted(groups.items()):
                files.sort(key=lambda f: f['path'])
                suffixes = [Path(f['path']).name.split('.part-')[-1] for f in files if '.part-' in f['path']]
                if suffixes:
                    nums = [sum((ord(c)-97)*26**i for i,c in enumerate(reversed(s))) for s in suffixes]
                    if nums != list(range(len(nums))):
                        raise ValueError(f'Missing archive part: {benchmark.name}/{kind}/{task}: {suffixes}')
                row = {'benchmark': benchmark.name.replace('_compressed', '_release'),
                       'embodiment': kind, 'task': task, 'parts': files,
                       'bytes': sum(f['size'] for f in files), 'instruction': instructions.get(task)}
                if kind not in SUPPORTED:
                    excluded.append(row)
                elif not row['instruction']:
                    missing.append(row)
                else:
                    archives.append(row)
    return {'root': str(root), 'archives': archives, 'unsupported': excluded,
            'missing_instructions': missing, 'bytes': sum(r['bytes'] for r in archives)}
