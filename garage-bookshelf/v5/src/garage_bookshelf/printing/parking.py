"""Verify published parking CAD, measured inputs and saved validation evidence."""
import math
from pathlib import Path

from garage_bookshelf.parking.artifacts import parking_stem
from garage_bookshelf.paths import ROOT, read_json, sha

METHOD = 'bmw-z4-e89-measured-wheel-cradle-v1'
REFERENCE = Path('studies/measured-tray-s51-b23-d10-t5p1')
REFERENCE_STEM = 'parking-tray-s51-b23-d10-t5p1'


def _file(root, relative, expected=None):
    if not isinstance(relative, str):
        raise ValueError('Parking artifact path must be a string')
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts or (expected is not None and path.as_posix() != str(expected)):
        raise ValueError('Parking artifact is in the wrong directory: ' + relative)
    file = (root / path).resolve()
    if not file.is_relative_to(root) or not file.is_file():
        raise ValueError('Parking artifact missing or outside this version: ' + relative)
    return file


def _measurements(values):
    if not isinstance(values, dict) or set(values) != {'S', 'Bf', 'Br', 'Df', 'Dr', 'Tf', 'Tr'}:
        raise ValueError('Parking insert must record all seven measurements')
    if any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in values.values()):
        raise ValueError('Parking measurements must be positive finite numbers')
    if (values['S'] <= (values['Df'] + values['Dr']) / 2 or
            values['Bf'] <= values['Tf'] or values['Br'] <= values['Tr']):
        raise ValueError('Parking measurements imply an invalid wheelbase or track')


def _legacy_reference(record, catalog, root):
    """The original BMW reference predates revision directories and files/location maps."""
    _file(root, record['evidence'], REFERENCE / 'validation.json')
    report = read_json(root / record['evidence'])
    if (report.get('status') != 'passed' or report.get('reopened_and_sliced') is not True or
            report.get('formal_cad_sha256') != catalog['cad_sha256']):
        raise ValueError('BMW reference verification is stale or incomplete')
    _measurements(report.get('measurements_mm'))
    files = report.get('sha256', {})
    for suffix in ('.FCStd', '.stl', '.3mf'):
        name = REFERENCE_STEM + suffix
        if sha(_file(root, (REFERENCE / name).as_posix())) != files.get(name):
            raise ValueError('BMW reference CAD or evidence changed: ' + name)
    expected_project = Path('parking-inserts/bmw-z4-e89') / (REFERENCE_STEM + '.3mf')
    project = _file(root, 'printing/' + record['project'], Path('printing') / expected_project)
    if (record['sha256'] != files[REFERENCE_STEM + '.3mf'] or sha(project) != record['sha256'] or
            catalog['files'].get(record['project']) != record['sha256']):
        raise ValueError('BMW reference project differs from its verification')


def _revision(record, catalog, root):
    variant, revision = record['id'], record.get('revision')
    stem = parking_stem(variant, revision)
    cad_dir = Path('cad/parking-inserts') / variant / revision
    printing_dir = Path('printing/parking-inserts') / variant / revision
    cad = _file(root, record['source_cad'], cad_dir / (stem + '.FCStd'))
    project = _file(root, 'printing/' + record['project'], printing_dir / (stem + '.3mf'))
    measurements = _file(root, record['measurements'], cad_dir / 'measurements.json')
    evidence = _file(root, record['evidence'], printing_dir / 'validation.json')
    outline = _file(root, (cad_dir / 'model-label-outline.json').as_posix())
    if sha(cad) != record['source_cad_sha256'] or sha(project) != record['sha256']:
        raise ValueError('Parking CAD or project changed: ' + stem)
    if (catalog['files'].get(record['project']) != record['sha256'] or
            catalog['files'].get(evidence.relative_to(root / 'printing').as_posix()) != sha(evidence)):
        raise ValueError('Parking project or report differs from the catalog: ' + stem)
    report, spec = read_json(evidence), read_json(measurements)
    if (report.get('status') != 'passed' or report.get('saved_project_reopened_and_sliced') is not True or
            report.get('source_cad') != catalog['source_cad'] or
            report.get('cad_sha256') != catalog['cad_sha256'] or
            report.get('variant') != variant or report.get('revision') != revision or
            spec.get('variant') != variant or spec.get('revision') != revision or
            report.get('interface') != record['interface'] or spec.get('interface') != record['interface'] or
            report.get('design_method') != record['design_method'] or
            report.get('model_label') != record['model_label'] or
            spec.get('model_label') != record['model_label'] or
            read_json(outline).get('text') != record['model_label']):
        raise ValueError('Parking verification does not match the registered variant: ' + stem)
    values = spec.get('measurements_mm')
    _measurements(values)
    if values != record.get('measurements_mm') or values != report.get('measurements_mm'):
        raise ValueError('Parking measurements differ between input, catalog and report: ' + stem)
    source = spec.get('measurement_source', {})
    if (not source or source != report.get('measurement_source') or
            sha(_file(root, source.get('path'))) != source.get('sha256')):
        raise ValueError('Parking measurement source missing, changed or inconsistent: ' + stem)
    if (type(record.get('physical_fit_tested')) is not bool or
            report.get('physical_fit_tested') is not record['physical_fit_tested']):
        raise ValueError('Parking physical-fit status differs from its report: ' + stem)

    files, locations = report.get('files', {}), report.get('artifact_locations', {})
    required = {stem + '.FCStd': cad, stem + '.3mf': project,
                'measurements.json': measurements, 'model-label-outline.json': outline,
                'slice-result.json': root / printing_dir / 'slice-result.json'}
    if not required.keys() <= files.keys() or files.keys() != locations.keys():
        raise ValueError('Parking verification is missing artifact hashes or locations: ' + stem)
    for name, digest in files.items():
        file = _file(root, locations[name])
        if (file.name != name or not (file.is_relative_to(root / cad_dir) or
                                      file.is_relative_to(root / printing_dir)) or
                (name in required and file != required[name].resolve()) or sha(file) != digest):
            raise ValueError('Parking verified artifact missing, changed or misplaced: ' + name)
        if file.is_relative_to(root / 'printing'):
            if catalog['files'].get(file.relative_to(root / 'printing').as_posix()) != digest:
                raise ValueError('Parking evidence hash differs from the catalog: ' + name)
    if files[cad.name] != record['source_cad_sha256'] or files[project.name] != record['sha256']:
        raise ValueError('Parking CAD or project hash differs from its report: ' + stem)
    result = read_json(required['slice-result.json'])
    plates = result.get('sliced_plates', [])
    if (result.get('return_code') != 0 or len(plates) != 1 or
            len(plates[0].get('objects', [])) != 1 or plates[0].get('warning_message')):
        raise ValueError('Parking saved slice result is not a passed single-object plate: ' + stem)


def verify_parking_inserts(catalog, root=ROOT):
    root = Path(root).resolve()
    seen = set()
    for record in catalog['parking_inserts']:
        try:
            key = (record['id'], record.get('revision'))
            if key in seen:
                raise ValueError('Duplicate parking insert revision')
            seen.add(key)
            if record.get('interface') != 'parking-base-v1' or record.get('design_method') != METHOD:
                raise ValueError('Unknown parking insert interface or design method')
            if record['id'] == 'bmw-z4-e89' and 'revision' not in record:
                _legacy_reference(record, catalog, root)
            else:
                _revision(record, catalog, root)
        except (KeyError, TypeError, AttributeError) as error:
            raise ValueError('Incomplete parking insert catalog or verification record') from error
