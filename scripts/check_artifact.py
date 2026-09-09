#!/usr/bin/env python3
"""Verify the generated ZIP byte inventory, then test its extracted payload offline."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import zipfile


def check(archive: Path) -> None:
    with tempfile.TemporaryDirectory(prefix='cer-artifact-') as tmp:
        target = Path(tmp)
        with zipfile.ZipFile(archive) as z:
            names = z.namelist()
            if len(names) != len(set(names)) or len(names) > 2000:
                raise ValueError('duplicate or oversized archive inventory')
            if sum(i.file_size for i in z.infolist()) > 64 * 1024 * 1024:
                raise ValueError('oversized archive payload')
            for info in z.infolist():
                path = PurePosixPath(info.filename)
                if (path.is_absolute() or '..' in path.parts or '\\' in info.filename
                        or not path.parts or path.parts[0] != 'codex-efficiency-router'
                        or (info.external_attr >> 16) & 0o170000 == 0o120000):
                    raise ValueError('unsafe archive member')
            z.extractall(target)
        root = target / 'codex-efficiency-router'
        manifest = json.loads((root / 'RELEASE-MANIFEST.json').read_text(encoding='utf-8'))
        files = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in root.rglob('*') if p.is_file() and p.name != 'RELEASE-MANIFEST.json'}
        if files != manifest['files']:
            raise ValueError('artifact byte inventory does not match manifest')
        from release_identity import sha, canonical
        if sha(canonical(files)) != manifest['source_tree_sha256']:
            raise ValueError('artifact tree hash mismatch')
        for argv in (['scripts/release_package.py', '--check', '--schema'],
                     ['scripts/doctor.py', '--source-tree', '.', '--json'],
                     ['-m', 'unittest', 'discover', '-s', 'tests', '-v']):
            subprocess.run([sys.executable, '-B', *argv], cwd=root, check=True)
        print('ARTIFACT_OFFLINE_PASS; native Canary, Windows host and published release NOT VERIFIED')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    try:
        check(parser.parse_args().archive)
        return 0
    except (ValueError, OSError, KeyError, zipfile.BadZipFile, subprocess.CalledProcessError) as exc:
        print(f'artifact: FAILED: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
