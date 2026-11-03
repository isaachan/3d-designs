"""Stage a complete component-organized candidate under build/, preserving printing/."""
import argparse
import os
from pathlib import Path
import re
import shutil
import tempfile
import _bootstrap
from garage_bookshelf.paths import CAD, ROOT, TMP, output_directory, read_json, sha, source_record, write_json
from garage_bookshelf.printing.manifests import verified_manifest
from garage_bookshelf.printing.components import project_destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--export-dir', required=True, type=Path)
    parser.add_argument('--print-dir', required=True, type=Path)
    parser.add_argument('--release-id', required=True)
    parser.add_argument('--render-dir', type=Path)
    parser.add_argument('--output', help='New or empty candidate directory under v5/build/')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}', args.release_id) or '..' in args.release_id:
        parser.error('Invalid release ID')
    exported = verified_manifest(args.export_dir, 'geometry-export')
    print_kind = read_json(args.print_dir/'manifest.json')['kind']
    if print_kind not in ('print-projects','colored-print-projects'):
        parser.error('Unsupported print manifest')
    printed = verified_manifest(args.print_dir, print_kind)
    if printed['cad_sha256'] != exported['cad_sha256']:
        parser.error('Geometry and print projects use different CAD versions')
    link = 'geometry_manifest_sha256' if print_kind == 'colored-print-projects' else 'export_manifest_sha256'
    if not printed['complete_plan'] or printed[link] != sha(args.export_dir / 'manifest.json'):
        parser.error('Print run is incomplete or comes from another export')
    plan = read_json(ROOT / 'printing/plate-plan.json')
    if plan['status'] != 'approved' or printed['plan_sha256'] != sha(ROOT / 'printing/plate-plan.json'):
        parser.error('Review the plate plan and mark it approved, then regenerate projects before releasing')
    if sorted(name for p in printed['projects'] for name in p['parts']) != sorted(p['part'] for p in exported['print_parts']):
        parser.error('Printable part coverage does not match the export')
    expected = {p['id']: p['parts'] for p in plan['plates']}
    if len(printed['projects']) != len(expected) or {p['id'] for p in printed['projects']} != set(expected):
        parser.error('Print projects must cover every planned plate exactly once')
    for plate in printed['projects']:
        if sorted(plate['parts']) != sorted(expected[plate['id']]):
            parser.error('Print project parts do not match the planned plate')
        if not plate['saved_project_reopened_and_sliced'] or plate['reload_profile_overrides'] or plate['warning_messages']:
            parser.error('A saved project has not passed independent slicing')
        if printed['files'].get(plate['project']) != plate['project_sha256']:
            parser.error('A project is not covered by the verified output files')
    target = output_directory(args.output, args.release_id + '-package')
    TMP.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='release-', dir=TMP) as temporary:
        stage = Path(temporary) / args.release_id
        for source, name, checked in [(args.export_dir, 'evidence/geometry', exported),
                                      (args.print_dir, 'evidence/print-run', printed)]:
            for relative in ['manifest.json', *checked['files']]:
                destination = stage / name / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source / relative, destination)
                if relative != 'manifest.json' and sha(destination) != checked['files'][relative]:
                    raise ValueError(f'Input changed during packaging: {relative}')
        (stage/'evidence/cad').mkdir(parents=True)
        shutil.copy2(CAD,stage/'evidence/cad'/CAD.name)
        shutil.copy2(ROOT/'cad/model-spec.json',stage/'evidence/cad/model-spec.json')
        shutil.copy2(ROOT/'printing/plate-plan.json',stage/'evidence/plate-plan.json')
        projects = []
        for plate in printed['projects']:
            source = args.print_dir / plate['project']
            relative = project_destination(plate['parts'], source.name)
            destination = stage / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            if sha(destination) != plate['project_sha256']:
                raise ValueError('Project differs from its verified record: ' + plate['id'])
            preview = source.with_suffix('.png')
            if preview.exists():
                preview_relative = str(preview.relative_to(args.print_dir))
                if printed['files'].get(preview_relative) != sha(preview):
                    raise ValueError('Project preview is not verified: ' + plate['id'])
                shutil.copy2(preview, destination.with_suffix('.png'))
            projects.append(dict(id=plate['id'], parts=plate['parts'],
                                 project=relative.as_posix(), project_sha256=sha(destination)))
        (stage/'parking-inserts').mkdir()
        (stage/'parking-inserts/README.md').write_text(
            '# 车型卡槽\n\n本包只生成主体与两块默认文字载板。车型卡槽按独立源文件和指定试配流程另行验证、选配。\n')
        if args.render_dir:
            render = read_json(args.render_dir/'render.json')
            if render['status'] != 'passed' or render['cad_sha256'] != exported['cad_sha256']:
                parser.error('Render does not match current CAD')
            (stage/'render').mkdir()
            shutil.copy2(args.render_dir/'assembly.png',stage/'render/assembly.png')
            shutil.copy2(args.render_dir/'render.json',stage/'render/render.json')
        seconds = sum(p['estimated_seconds'] for p in printed['projects'])
        grams = sum(p['estimated_filament_g'] for p in printed['projects'])
        minutes = round(seconds/60)
        title = '# garage-bookshelf v5 · '+args.release_id+'\n\n'
        intro = ('黑色主体＋齐平内嵌三色饰片。05/06为0.20mm、4圈墙、25%填充的单色主体；'
                 '13–15各含4片0.6mm饰片，落在0.6mm深承托面上，另设0.2mm胶槽。先拼接主体再装饰片。其余盘保留CAD多色涂色。\n\n') if print_kind == 'colored-print-projects' else '单材料分盘，CAD多色外观需另行填色。\n\n'
        text = title+intro+f"共{len(printed['projects'])}盘、{len(exported['print_parts'])}个打印件；切片估算{grams:.1f}g、{minutes//60}小时{minutes%60:02d}分；按80元/kg材料费{grams*.08:.2f}元。\n\n"
        text += '[当前组装说明]('+os.path.relpath(ROOT/'docs/assembly.md',target)+') · [源CAD快照](evidence/cad/'+CAD.name+')\n\n'
        if args.render_dir:text += '![原生CAD装配预览](render/assembly.png)\n\n'
        rows = ['| 3MF | 用料 g | 时间 min |','|---|---:|---:|'] + [
            f"| [{p['id']}]({r['project']}) | {p['estimated_filament_g']:.1f} | {p['estimated_seconds']/60:.0f} |"
            for p, r in zip(printed['projects'], projects)]
        text += '\n'.join(rows)+'\n\n这是build内的候选包，未更新当前printing文件；个人设置与可选车型不在自动替换范围。原始生成清单和输入保存在evidence中。STEP含8个外购硬件；STL和3MF不含硬件、托座样件及零厚度外观面。全部保存项目已重新打开实际切片；未实物试配、粘接或承重验证，不交付G-code。80元/kg仅为预算情景；3MF预设单价19.99/kg未指定币种，请按实际购入价修改。材料费不含胶、电费、人工、外购件和失败重打。\n'
        (stage/'README.md').write_text(text)
        if sha(CAD) != exported['cad_sha256']:
            raise ValueError('CAD changed during packaging; do not release stale data')
        manifest = dict(source_record(), status='passed', kind='release',
                        release_id=args.release_id, physical_print_and_fit_tested=False,
                        projects=projects, current_printing_modified=False,
                        print_kind=print_kind,print_part_count=len(exported['print_parts']),
                        plate_count=len(printed['projects']),estimated_filament_g=grams,estimated_seconds=seconds,
                        files={str(p.relative_to(stage)): sha(p) for p in stage.rglob('*') if p.is_file()})
        write_json(stage / 'package-manifest.json', manifest)
        target.rmdir()  # Only an empty build target may be replaced by the staged directory.
        stage.rename(target)
    print('PASS', target)


if __name__ == '__main__':
    main()
