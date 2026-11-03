"""Route current print projects to the three product component families."""
from pathlib import Path

SIGN_PARTS = {'top_carrier': 'upper', 'side_cartridge': 'side'}


def project_destination(parts, filename):
    """Keep replaceable text carriers separate from the unlettered main structure."""
    if not parts or Path(filename).name != filename or not filename.endswith('.3mf'):
        raise ValueError('Expected parts and a plain 3MF filename')
    carriers = set(parts) & SIGN_PARTS.keys()
    if carriers:
        if len(parts) != 1:
            raise ValueError('A text carrier must have its own print project')
        return Path('sign-carriers') / SIGN_PARTS[parts[0]] / 'default' / filename
    return Path('main/3mf') / filename
