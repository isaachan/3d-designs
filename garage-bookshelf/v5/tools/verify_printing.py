"""Read-only check of the component catalog, current artifacts and provenance."""
import _bootstrap
from garage_bookshelf.paths import CAD, ROOT, read_json, sha
from garage_bookshelf.printing.components import project_destination


def verify():
    printing = ROOT / 'printing'
    catalog = read_json(printing / 'catalog.json')
    if catalog['cad_sha256'] != sha(CAD):
        raise ValueError('Catalog belongs to another CAD revision')
    for relative, digest in catalog['files'].items():
        file = (printing / relative).resolve()
        if not file.is_relative_to(printing.resolve()) or not file.is_file() or sha(file) != digest:
            raise ValueError('Current artifact missing, changed or outside printing/: ' + relative)
    actual = {p.relative_to(printing).as_posix() for p in printing.rglob('*.3mf')}
    listed = {p for p in catalog['files'] if p.endswith('.3mf')}
    if actual != listed:
        raise ValueError('Unlisted or missing 3MF files in printing/')
    projects = catalog['default_projects']
    plan = read_json(printing / 'plate-plan.json')
    expected = {p['id']: p['parts'] for p in plan['plates']}
    if len(projects) != len(expected) or {p['id'] for p in projects} != set(expected):
        raise ValueError('Default projects do not cover the plate plan')
    for project in projects:
        relative = project['project']
        if sorted(project['parts']) != sorted(expected[project['id']]):
            raise ValueError('Part list differs from plate plan: ' + project['id'])
        if relative != project_destination(project['parts'], relative.split('/')[-1]).as_posix():
            raise ValueError('Project is in the wrong product component: ' + relative)
        if catalog['files'].get(relative) != project['project_sha256']:
            raise ValueError('Project hash differs from catalog file list: ' + relative)
    spec = read_json(ROOT / 'cad/model-spec.json')
    parts = [part for project in projects for part in project['parts']]
    if sorted(parts) != sorted(spec['print_parts']) or len(parts) != len(set(parts)):
        raise ValueError('Default printable parts are missing or duplicated')
    components = catalog['components']
    if sorted(components['main'] + components['sign_carriers']) != sorted(parts):
        raise ValueError('Component part lists do not cover the default configuration')
    if components['sign_carriers'] != ['top_carrier', 'side_cartridge'] or components['parking_inserts'] != spec['samples']:
        raise ValueError('Carrier or sample roles differ from the model specification')
    counts = (len(projects), len(parts), len(components['main']), len(components['sign_carriers']))
    recorded = tuple(catalog[k] for k in ('default_plate_count', 'default_print_part_count',
                                         'main_print_part_count', 'default_carrier_part_count'))
    if counts != recorded:
        raise ValueError('Catalog component counts are inconsistent')
    records = catalog['preserved_personal_projects'] + catalog['parking_inserts']
    for record in records:
        if catalog['files'].get(record['project']) != record['sha256']:
            raise ValueError('Variant hash differs from catalog: ' + record['project'])
    for record in catalog['provenance']:
        source = (ROOT / record['source']).resolve()
        if not source.is_relative_to(ROOT.resolve()) or not source.is_file() or sha(source) != record['sha256']:
            raise ValueError('Preserved source differs: ' + record['source'])
        if catalog['files'].get(record['path']) != record['sha256']:
            raise ValueError('Provenance differs from catalog: ' + record['path'])
    print('PASS: 3 component families;', len(projects), 'default plates;', len(parts),
          'parts;', len(catalog['preserved_personal_projects']), 'personal projects preserved')


if __name__ == '__main__':
    verify()
