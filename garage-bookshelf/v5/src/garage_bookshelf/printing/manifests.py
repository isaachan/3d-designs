"""Reject stale, missing or changed inputs before generating or releasing files."""
from pathlib import Path
from garage_bookshelf.paths import CAD, sha, read_json


def verified_manifest(directory, kind):
    directory = Path(directory).resolve()
    manifest = read_json(directory / 'manifest.json')
    if manifest.get('status') != 'passed' or manifest.get('kind') != kind:
        raise ValueError(f'Expected passed {kind} manifest: {directory}')
    if manifest['cad_sha256'] != sha(CAD):
        raise ValueError('Source CAD changed: regenerate rather than reusing stale output')
    if not manifest.get('files'):
        raise ValueError('Manifest has no verified output files')
    for relative, digest in manifest['files'].items():
        file = (directory / relative).resolve()
        if not file.is_relative_to(directory) or not file.is_file() or sha(file) != digest:
            raise ValueError(f'Output missing, changed or outside run directory: {relative}')
    return manifest
