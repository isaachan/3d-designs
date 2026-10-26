"""One project root for libraries, tools and independently runnable studies."""
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
CAD = ROOT / 'cad/garage-bookshelf-v5-assembly.FCStd'
LETTERING = ROOT / 'assets/lettering'
PROFILES = ROOT / 'assets/print-profiles'
BUILD = ROOT / 'build'
TMP = BUILD / 'tmp'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def source_record(cad=CAD):
    try:
        result = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT,
                                capture_output=True, text=True)
        commit = result.stdout.strip() if result.returncode == 0 else None
    except FileNotFoundError:
        commit = None
    return dict(source_cad=str(Path(cad).resolve().relative_to(ROOT)),
                cad_sha256=sha(cad), source_git_commit=commit,
                code_files_sha256={str(p.relative_to(ROOT)): sha(p)
                    for folder in ('src', 'tools') for p in sorted((ROOT / folder).rglob('*.py'))},
                generated_at=datetime.now(timezone.utc).isoformat())


def output_directory(value=None, label='run'):
    """Generated files stay in build/; never overwrite source or reviewed projects."""
    target = Path(value).expanduser() if value else BUILD / (
        datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-' + label)
    if not target.is_absolute():
        target = ROOT / target
    target = target.resolve()
    if not target.is_relative_to(BUILD.resolve()) or target == BUILD.resolve():
        raise ValueError('Generated output must be a subdirectory of v5/build/')
    if target.exists() and any(target.iterdir()):
        raise FileExistsError(f'Output is not empty: {target}')
    target.mkdir(parents=True, exist_ok=True)
    return target


def study_directory(name):
    """Historical trial regenerations never overwrite their saved artifacts."""
    parser = argparse.ArgumentParser(description='Regenerate a study into build/, preserving saved evidence.')
    parser.add_argument('--output', default=str(BUILD / 'studies' / name))
    args = parser.parse_args()
    target = Path(args.output).expanduser().resolve()
    if not target.is_relative_to(BUILD.resolve()) or target == BUILD.resolve():
        parser.error('--output must be a subdirectory of v5/build/')
    target.mkdir(parents=True, exist_ok=True)
    return target
