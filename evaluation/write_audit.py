"""Separate offline write-boundary mutations and source hashes; no model calls."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

from write_mutations import run

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    output = ROOT / 'evaluation-results'
    output.mkdir(exist_ok=True)
    mutations = run(ROOT, output)
    files = [*sorted((ROOT / 'hooks').glob('*.py')), ROOT / 'scripts/write_policy.py',
             ROOT / 'scripts/write_guard.py', ROOT / 'scripts/effort_reference.py',
             *sorted((ROOT / 'tests').glob('test_*write*.py'))]
    report = {
        'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'mutations': mutations,
        'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        'native_host_enforcement': 'NOT VERIFIED; real guard exercised by synthetic-host tests in unittest suite',
        'model_calls': 0,
    }
    (output / 'write-boundary-report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    return int(any(m['outcome'] != 'KILLED' for m in mutations))


if __name__ == '__main__':
    raise SystemExit(main())
