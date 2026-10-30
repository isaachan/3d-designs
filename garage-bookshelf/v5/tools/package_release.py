"""Package a complete verified print set under printing/<release-id>/."""
import argparse
from pathlib import Path
import re
import shutil
import tempfile
import _bootstrap
from garage_bookshelf.paths import CAD, ROOT, TMP, read_json, sha, source_record, write_json
from garage_bookshelf.printing.manifests import verified_manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--export-dir', required=True, type=Path)
    parser.add_argument('--print-dir', required=True, type=Path)
    parser.add_argument('--release-id', required=True)
    parser.add_argument('--render-dir', type=Path)
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
    for plate in printed['projects']:
        if not plate['saved_project_reopened_and_sliced'] or plate['reload_profile_overrides'] or plate['warning_messages']:
            parser.error('A saved project has not passed independent slicing')
    target = ROOT / 'printing' / args.release_id
    if target.exists():
        parser.error('Release already exists; create a new ID')
    TMP.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='release-', dir=TMP) as temporary:
        stage = Path(temporary) / args.release_id
        for source, name, checked in [(args.export_dir, 'geometry', exported),
                                      (args.print_dir, '', printed)]:
            for relative in ['manifest.json', *checked['files']]:
                destination = stage / name / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source / relative, destination)
                if relative != 'manifest.json' and sha(destination) != checked['files'][relative]:
                    raise ValueError(f'Input changed during packaging: {relative}')
        (stage/'cad').mkdir()
        shutil.copy2(CAD,stage/'cad'/CAD.name)
        shutil.copy2(ROOT/'cad/model-spec.json',stage/'cad/model-spec.json')
        shutil.copy2(ROOT/'printing/plate-plan.json',stage/'plate-plan.json')
        shutil.copy2(ROOT/'docs/assembly.md',stage/'ASSEMBLY.md')
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
        rows = ['| 3MF | 用料 g | 时间 min |','|---|---:|---:|']
        for p in printed['projects']:
            rows.append(f"| [{p['id']}]({p['project']}) | {p['estimated_filament_g']:.1f} | {p['estimated_seconds']/60:.0f} |")
        text = title+intro+f"共{len(printed['projects'])}盘、{len(exported['print_parts'])}个打印件；切片估算{grams:.1f}g、{minutes//60}小时{minutes%60:02d}分；按80元/kg材料费{grams*.08:.2f}元。\n\n"
        text += '[装配步骤](ASSEMBLY.md) · [完整CAD](cad/'+CAD.name+')\n\n'
        if args.render_dir:text += '![原生CAD装配预览](render/assembly.png)\n\n'
        text += '\n'.join(rows)+'\n\nSTEP含8个外购硬件；STL和3MF不含硬件、托座样件及零厚度外观面。全部保存项目已重新打开实际切片；未实物试配、粘接或承重验证，不交付G-code。80元/kg仅为预算情景；3MF预设单价19.99/kg未指定币种，请按实际购入价修改。材料费不含胶、电费、人工、外购件和失败重打。\n'
        (stage/'README.md').write_text(text)
        if sha(CAD) != exported['cad_sha256']:
            raise ValueError('CAD changed during packaging; do not release stale data')
        manifest = dict(source_record(), status='passed', kind='release',
                        release_id=args.release_id, physical_print_and_fit_tested=False,
                        print_kind=print_kind,print_part_count=len(exported['print_parts']),
                        plate_count=len(printed['projects']),estimated_filament_g=grams,estimated_seconds=seconds,
                        files={str(p.relative_to(stage)): sha(p) for p in stage.rglob('*') if p.is_file()})
        write_json(stage / 'package-manifest.json', manifest)
        stage.rename(target)
    print('PASS', target)


if __name__ == '__main__':
    main()
