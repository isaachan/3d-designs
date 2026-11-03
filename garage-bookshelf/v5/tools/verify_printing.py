"""Read-only check of the component catalog, current artifacts and provenance."""
from pathlib import Path
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
    custom_carriers = catalog.get('custom_carriers', [])
    records = catalog['preserved_personal_projects'] + catalog['parking_inserts'] + custom_carriers
    for record in records:
        if catalog['files'].get(record['project']) != record['sha256']:
            raise ValueError('Variant hash differs from catalog: ' + record['project'])
    for record in custom_carriers:
        position, variant = record['position'], record['id']
        if position not in ('upper', 'side') or record['interface'] != 'sign-' + position + '-v1':
            raise ValueError('Unknown custom carrier interface')
        prefix = f'sign-carriers/{position}/{variant}/'
        if not record['project'].startswith(prefix) or (Path(record['project']).parent.as_posix() + '/') != prefix:
            raise ValueError('Custom carrier is in the wrong component directory')
        cad = (ROOT / record['source_cad']).resolve()
        expected_cad = ROOT / f'cad/sign-carriers/{position}/{variant}/{variant}.FCStd'
        if cad != expected_cad.resolve() or not cad.is_file() or sha(cad) != record['source_cad_sha256']:
            raise ValueError('Custom carrier CAD missing or changed')
        evidence = (ROOT / record['evidence']).resolve()
        if not evidence.is_relative_to(printing.resolve()):
            raise ValueError('Custom carrier evidence must be in its printing directory')
        checked = read_json(evidence)
        if (checked['status'] != 'passed' or not checked['saved_project_reopened_and_sliced'] or
            checked['position'] != position or checked['variant'] != variant or
            checked['interface'] != record['interface'] or checked['text'] != record['text'] or
            checked['files'][cad.name] != record['source_cad_sha256'] or
            checked['files'][Path(record['project']).name] != record['sha256']):
            raise ValueError('Custom carrier verification does not match its source or project')
    for record in catalog['provenance']:
        source = (ROOT / record['source']).resolve()
        if not source.is_relative_to(ROOT.resolve()) or not source.is_file() or sha(source) != record['sha256']:
            raise ValueError('Preserved source differs: ' + record['source'])
        if catalog['files'].get(record['path']) != record['sha256']:
            raise ValueError('Provenance differs from catalog: ' + record['path'])
    print('PASS: 3 component families;', len(projects), 'default plates;', len(parts),
          'parts;', len(catalog['preserved_personal_projects']), 'personal projects preserved;',
          len(custom_carriers), 'custom text carriers')


if __name__ == '__main__':
    verify()
