"""Generate selected single-material projects from a current verified export."""
import argparse
from pathlib import Path
import tempfile
from zipfile import ZipFile
import _bootstrap
from garage_bookshelf.paths import CAD, ROOT, TMP, PROFILES, output_directory, read_json, sha, source_record, write_json
from garage_bookshelf.printing.bambu import run_cli, read_settings
from garage_bookshelf.printing.manifests import verified_manifest
from garage_bookshelf.printing.threemf import project_bounds


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--export-dir', required=True, type=Path, help='Geometry-export directory containing manifest.json')
    parser.add_argument('--plan', type=Path, default=ROOT / 'printing/plate-plan.json')
    parser.add_argument('--only', nargs='+', help='Optional subset of plate IDs')
    parser.add_argument('--output', help='Empty output directory under v5/build/')
    args = parser.parse_args()
    source = args.export_dir.resolve()
    exported = verified_manifest(source, 'geometry-export')
    plan = read_json(args.plan)
    ids = {p['id'] for p in plan['plates']}
    if args.only and not set(args.only) <= ids:
        parser.error('--only contains unknown plate IDs')
    by_name = {p['part']: p for p in exported['print_parts']}
    flat_parts = [name for p in plan['plates'] for name in p['parts']]
    if len(flat_parts) != len(set(flat_parts)) or set(flat_parts) != set(by_name):
        parser.error('Plate plan must cover every exported print part exactly once')
    output = output_directory(args.output, 'print')
    (output / '3mf').mkdir()
    (output / 'logs').mkdir()
    TMP.mkdir(parents=True, exist_ok=True)
    records = []
    for plate in plan['plates']:
        if args.only and plate['id'] not in args.only:
            continue
        print('Preparing', plate['id'], flush=True)
        files = [source / by_name[name]['print_file'] for name in plate['parts']]
        project = output / '3mf' / (plate['id'] + '.3mf')
        color, supports = plate['color'], plate['supports']
        process = PROFILES / ('PLA-0.20-support-process.json' if supports else 'PLA-0.20-process.json')
        with tempfile.TemporaryDirectory(prefix=plate['id'] + '-', dir=TMP) as temp:
            scratch = Path(temp)
            run_cli(['--load-settings', f'{PROFILES / "X2D-0.4-standard-machine.json"};{process}',
                     '--load-filaments', PROFILES / f'PLA-{color}.json', '--orient', '0', '--arrange', '1',
                     '--export-3mf', project, *files], scratch / 'export-state', output / 'logs' / (plate['id'] + '-export.log'))
            settings = read_settings(project, color, supports)
            bounds = project_bounds(project)
            assert len(bounds) == len(files)
            sliced = scratch / 'sliced'
            sliced.mkdir()
            run_cli(['--orient', '0', '--arrange', '0', '--outputdir', sliced, '--slice', '0', project],
                    scratch / 'reload-state', output / 'logs' / (plate['id'] + '-slice.log'))
            result = read_json(sliced / 'result.json')
            assert result['return_code'] == 0 and len(result['sliced_plates']) == 1
            saved = result['sliced_plates'][0]
            assert len(saved['objects']) == len(files) and not saved['warning_message']
            assert saved['filament_change_times'] == 0 and len(saved['filaments']) == 1
            write_json(output / 'logs' / (plate['id'] + '-result.json'), result)
        with ZipFile(project) as z:
            project.with_suffix('.png').write_bytes(z.read('Metadata/plate_1.png'))
        records.append(dict(id=plate['id'], parts=plate['parts'], project=str(project.relative_to(output)),
                            input_sha256={name: sha(file) for name, file in zip(plate['parts'], files)},
                            project_sha256=sha(project), settings=settings, object_bounds=bounds,
                            saved_project_reopened_and_sliced=True, reload_profile_overrides=False,
                            warning_messages=[], estimated_seconds=saved['total_predication'],
                            estimated_filament_g=saved['filaments'][0]['total_used_g']))
    if sha(CAD) != exported['cad_sha256']:
        raise ValueError('CAD changed while preparing projects; regenerate from a fresh export')
    manifest = dict(source_record(), status='passed', kind='print-projects',
                    export_manifest_sha256=sha(source / 'manifest.json'),
                    plan_sha256=sha(args.plan), plan_status=plan['status'],
                    complete_plan=len(records) == len(plan['plates']), projects=records,
                    color_mode='single-material; CAD surface colors require separate finishing/mapping',
                    physical_print_and_fit_tested=False, gcode_delivered=False)
    manifest['files'] = {str(p.relative_to(output)): sha(p) for p in output.rglob('*') if p.is_file()}
    write_json(output / 'manifest.json', manifest)
    print('PASS', len(records), 'projects;', output)


if __name__ == '__main__':
    main()
