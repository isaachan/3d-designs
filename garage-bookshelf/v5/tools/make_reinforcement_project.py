"""Export only the four CAD reinforcement plates and verify one X2D print project."""
import argparse
from pathlib import Path
import tempfile
from zipfile import ZipFile

import _bootstrap
import FreeCAD as App
import Mesh
import MeshPart
from garage_bookshelf.assembly import global_shape
from garage_bookshelf.paths import CAD, PROFILES, TMP, output_directory, read_json, sha, source_record, write_json
from garage_bookshelf.reinforcement import PLATES, check
from garage_bookshelf.printing.bambu import run_cli, read_settings
from garage_bookshelf.printing.threemf import project_bounds


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output')
    args = parser.parse_args()
    output = output_directory(args.output, 'reinforcement-print')
    for folder in ('stl', 'logs', 'profiles'):
        (output/folder).mkdir()
    before = sha(CAD)
    doc = App.openDocument(str(CAD))
    try:
        checks = check(doc)
        files = []
        for name, *_ in PLATES:
            shape = global_shape(doc.getObject(name+'_Body'))
            mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=.02, AngularDeflection=.12, Relative=False)
            mesh.transform(App.Placement(App.Vector(), App.Rotation(App.Vector(1, 0, 0), 90)).toMatrix())
            box = mesh.BoundBox
            mesh.translate(-box.XMin, -box.YMin, -box.ZMin)
            file = output/'stl'/f'{name}.stl'
            mesh.write(str(file))
            restored = Mesh.Mesh(str(file))
            assert restored.isSolid() and not restored.hasNonManifolds(), name
            assert len(restored.getSeparateComponents()) == 1, name
            box = restored.BoundBox
            assert max(abs(actual-expected) for actual, expected in
                       zip((box.XLength, box.YLength, box.ZLength), (60, 30, 3))) < 1e-5, name
            assert abs(abs(restored.Volume)-5400) < .01, name
            files.append(file)
    finally:
        App.closeDocument(doc.Name)
    overrides = dict(sparse_infill_density='100%', sparse_infill_pattern='zig-zag', enable_prime_tower='0')
    process = read_json(PROFILES/'PLA-0.20-process.json')
    process.update(overrides)
    process_file = output/'profiles/16-reinforcement-process.json'
    write_json(process_file, process)
    project = output/'16-reinforcement-plates-only.3mf'
    TMP.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='reinforcement-', dir=TMP) as temp:
        scratch = Path(temp)
        run_cli(['--load-settings', f'{PROFILES/"X2D-0.4-standard-machine.json"};{process_file}',
                 '--load-filaments', PROFILES/'PLA-black.json', '--orient', '0', '--arrange', '1',
                 '--export-3mf', project, *files], scratch/'export-state', output/'logs/export.log')
        settings = read_settings(project, 'black', False, overrides)
        bounds = project_bounds(project)
        assert len(bounds) == 4
        for item in bounds:
            dimensions = sorted(hi-lo for lo, hi in zip(item['min_mm'], item['max_mm']))
            assert max(abs(a-b) for a, b in zip(dimensions, (3, 30, 60))) < .001
        # The delivered file itself is reopened with its saved profiles, without overrides.
        sliced = scratch/'sliced'
        sliced.mkdir()
        run_cli(['--orient', '0', '--arrange', '0', '--outputdir', sliced, '--slice', '0', project],
                scratch/'reload-state', output/'logs/slice.log')
        result = read_json(sliced/'result.json')
        assert result['return_code'] == 0 and len(result['sliced_plates']) == 1
        plate = result['sliced_plates'][0]
        assert len(plate['objects']) == 4 and not plate['warning_message']
        assert plate['filament_change_times'] == 0 and len(plate['filaments']) == 1
        write_json(output/'slice-result.json', result)
    with ZipFile(project) as archive:
        assert archive.testzip() is None
        project.with_suffix('.png').write_bytes(archive.read('Metadata/plate_1.png'))
    assert sha(CAD) == before
    report = dict(source_record(), status='passed', kind='reinforcement-only-print-project',
        project=project.name, project_sha256=sha(project), print_part_count=4,
        parts=[row[0] for row in PLATES], dimensions_mm=[60, 30, 3], material='black PLA',
        mesh_closed_single_component=True, plates=checks, settings=settings, object_bounds=bounds,
        saved_project_reopened_and_sliced=True, warning_messages=[],
        estimated_seconds=plate['total_predication'], estimated_filament_g=plate['filaments'][0]['total_used_g'],
        physical_print_and_fit_tested=False, gcode_delivered=False)
    report['files'] = {str(f.relative_to(output)): sha(f) for f in output.rglob('*') if f.is_file()}
    write_json(output/'manifest.json', report)
    print('PASS', project, 'seconds', report['estimated_seconds'], 'grams', report['estimated_filament_g'], flush=True)


if __name__ == '__main__':
    main()
