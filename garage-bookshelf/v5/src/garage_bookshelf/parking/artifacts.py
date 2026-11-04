"""CAD-independent identifiers and output bounds for measured parking inserts."""
from pathlib import Path
import re

from garage_bookshelf.paths import BUILD


def parking_stem(variant, revision):
    for label, value in (('variant', variant), ('revision', revision)):
        if not isinstance(value, str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', value):
            raise ValueError(f'{label} must be a lowercase hyphenated identifier')
    return variant + '-' + revision


def output_artifact(directory, relative):
    """Check the resolved destination before a generator opens it for writing."""
    directory = Path(directory).resolve()
    relative = Path(relative)
    if directory == BUILD.resolve() or not directory.is_relative_to(BUILD.resolve()):
        raise ValueError('Parking output must be a subdirectory of v5/build/')
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('Parking artifact must use a relative path inside its output directory')
    target = (directory / relative).resolve()
    if target == directory or not target.is_relative_to(directory):
        raise ValueError('Parking artifact escapes its output directory')
    if target.exists():
        raise FileExistsError(f'Parking artifact already exists: {target}')
    return target
