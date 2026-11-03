#!/usr/bin/env python3
"""Verify the saved 3MFs, write material/time totals and package delivery."""
import collections
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
NS = {'c':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02',
      'p':'http://schemas.microsoft.com/3dmanufacturing/production/2015/06'}
COLOR_LABEL = dict(black='黑色', white='白色', lightblue='浅蓝', darkblue='深蓝', red='红色')


def sha(file):
    return hashlib.sha256(Path(file).read_bytes()).hexdigest()


def duration(seconds):
    minutes = round(seconds/60)
    return f'{minutes//60}小时{minutes%60:02d}分'


def source_triangles(part):
    import Mesh
    triangles = []
    for vol in part['volumes']:
        mesh = Mesh.Mesh(str(ROOT/vol['file']))
        vertices, faces = mesh.Topology
        triangles.extend([[list(vertices[i]) for i in face] for face in faces])
    return triangles


def delivered_triangles(file):
    with ZipFile(file) as z:
        cfg = ET.fromstring(z.read('Metadata/model_settings.config'))
        names = {o.get('id'):next(m.get('value') for m in o.findall('metadata') if m.get('key')=='name') for o in cfg.findall('object')}
        top = ET.fromstring(z.read('3D/3dmodel.model'))
        result = {}
        for obj in top.findall('c:resources/c:object', NS):
            triangles = []
            for component in obj.findall('c:components/c:component', NS):
                path = component.get('{'+NS['p']+'}path').lstrip('/')
                model = ET.fromstring(z.read(path))
                mesh = next(o for o in model.findall('c:resources/c:object', NS) if o.get('id')==component.get('objectid')).find('c:mesh', NS)
                points = [[float(v.get(a)) for a in 'xyz'] for v in mesh.findall('c:vertices/c:vertex', NS)]
                text = component.get('transform', '1 0 0 0 1 0 0 0 1 0 0 0')
                m = list(map(float, text.split()))
                points = [[sum(p[j]*m[3*j+i] for j in range(3))+m[9+i] for i in range(3)] for p in points]
                for tri in mesh.findall('c:triangles/c:triangle', NS):
                    triangles.append([points[int(tri.get(k))] for k in ('v1', 'v2', 'v3')])
            result[names[obj.get('id')]] = triangles
        return result


def geometry_deviation(source, saved):
    """Compare actual triangles rather than unstable decimal-grid hashes.

    Bambu recenters parts using float coordinates, so a vertex exactly on a
    rounding-grid boundary can change its hash despite sub-micron agreement.
    """
    import numpy as np
    from scipy.spatial import cKDTree
    a, b = np.asarray(source), np.asarray(saved)
    assert a.shape==b.shape, (a.shape, b.shape)
    a = a-a.min(axis=(0,1))
    b = b-b.min(axis=(0,1))
    def check(query, reference):
        k = min(4, len(reference))
        _, indexes = cKDTree(reference.mean(axis=1)).query(query.mean(axis=1), k=k)
        if k==1:
            indexes = indexes[:,None]
        maximum = 0.
        for lo in range(0, len(query), 2048):
            qq = query[lo:lo+2048]
            rr = reference[indexes[lo:lo+2048]]
            distance = np.linalg.norm(qq[:,None,:,None,:]-rr[:,:,None,:,:], axis=-1)
            hausdorff = np.maximum(distance.min(axis=-1).max(axis=-1), distance.min(axis=-2).max(axis=-1))
            maximum = max(maximum, float(hausdorff.min(axis=1).max()))
        return maximum
    maximum = max(check(a,b), check(b,a))
    assert maximum < .0001, maximum
    return maximum


def contact_sheet(rows):
    from PIL import Image, ImageDraw, ImageFont
    columns, w, h = 5, 350, 300
    rows_n = math.ceil(len(rows)/columns)
    image = Image.new('RGB', (columns*w, rows_n*h+110), '#f4f6f8')
    draw = ImageDraw.Draw(image)
    font_path = '/System/Library/Fonts/Hiragino Sans GB.ttc'
    title = ImageFont.truetype(font_path, 32)
    font = ImageFont.truetype(font_path, 18)
    small = ImageFont.truetype(font_path, 16)
    draw.text((25, 18), 'Parking Lot v1 · X2D 0.4 / PLA / 0.20 mm', font=title, fill='#20323d')
    draw.text((25, 62), '00 为接头试片；01–33 为完整装配件。每盘均已重开切片。', font=font, fill='#536674')
    for i, row in enumerate(rows):
        x, y = (i%columns)*w, (i//columns)*h+110
        thumb = Image.open((ROOT/row['project']).with_suffix('.png')).convert('RGBA')
        background = Image.new('RGBA', thumb.size, '#f4f6f8')
        background.alpha_composite(thumb)
        thumb = background.convert('RGB')
        thumb.thumbnail((330, 225))
        image.paste(thumb, (x+(w-thumb.width)//2, y))
        draw.text((x+12, y+227), row['id'], font=small, fill='#20323d')
        draw.text((x+12, y+252), f'{row["grams"]:.1f} g · {duration(row["seconds"])}', font=font, fill='#536674')
    image.save(ROOT/'plate-overview.png')


def main():
    sys.path.insert(0, '/Applications/FreeCAD.app/Contents/Resources/lib')
    import FreeCAD
    parts = json.loads((ROOT/'parts.json').read_text())
    plan = json.loads((ROOT/'plate-plan.json').read_text())['plates']
    geometry = json.loads((ROOT/'geometry-validation.json').read_text())
    assert geometry['status']=='passed'
    source = ROOT.parents[2]/parts['source_cad']
    assert sha(source)==parts['source_sha256']
    by = {p['name']:p for p in parts['parts']}
    summaries, checks = [], []
    for plate in plan:
        row = json.loads((ROOT/'results'/f'{plate["id"]}-summary.json').read_text())
        assert row['parts']==plate['parts']
        assert sha(ROOT/row['project'])==row['sha256']
        assert all(sha(ROOT/f)==s for f,s in row['source_mesh_hashes'].items()), plate['id']
        assert row['saved_project_reopened_and_sliced'] and not row['warning_message']
        delivered = delivered_triangles(ROOT/row['project'])
        assert set(delivered)==set(row['parts'])
        deviation = max(geometry_deviation(source_triangles(by[name]), delivered[name]) for name in row['parts'])
        summaries.append(row)
        checks.append(dict(plate=plate['id'], project_sha256=row['sha256'], mesh_geometry_preserved=True,
                           maximum_mesh_vertex_deviation_mm=deviation,
                           mechanical_parts=len(delivered), reloaded_slice_passed=True))
        print('VERIFIED', plate['id'], flush=True)
    intended = {Path(r['project']).name for r in summaries}
    for old in (ROOT/'3mf').glob('*.3mf'):
        if old.name not in intended:
            old.unlink()
            old.with_suffix('.png').unlink(missing_ok=True)
    colors = collections.defaultdict(float)
    main_colors = collections.defaultdict(float)
    for row in summaries:
        for f in row['materials']:
            colors[f['color']] += f['grams']
            main_colors[f['color']] += f['main_grams']
    production = [r for r in summaries if not r['id'].startswith('00-')]
    report = dict(status='passed', date='2026-11-03', printer='Bambu Lab X2D', nozzle_mm=.4, layer_height_mm=.2,
                  material='PLA', infill='25% with 4 walls; small pins/straps and test coupons 100%',
                  project_count=len(summaries), plate_count=len(summaries), production_plate_count=len(production),
                  production_print_parts=sum(len(r['parts']) for r in production), test_print_parts=4,
                  total_grams=sum(r['grams'] for r in summaries), total_seconds=sum(r['seconds'] for r in summaries),
                  production_grams=sum(r['grams'] for r in production), production_seconds=sum(r['seconds'] for r in production),
                  test_grams=summaries[0]['grams'], test_seconds=summaries[0]['seconds'],
                  filament_grams=dict(colors), main_filament_grams=dict(main_colors),
                  source_cad_unchanged=True, all_saved_projects_reopened_and_sliced=True,
                  all_delivery_meshes_match_source=True, all_mechanical_print_parts_connected=True,
                  warnings=[], purchased_hardware_excluded=True, physical_print_and_fit_tested=False,
                  estimates_include='Slicer total filament usage and total predicted time, including generated support and colour-change/prime estimates',
                  estimates_exclude='Manual plate changes, cooling/removal, fitting, glue curing and assembly',
                  plates=summaries, geometry_checks=checks)
    (ROOT/'summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    output = io.StringIO()
    writer = csv.writer(output, lineterminator='\n')
    writer.writerow(['plate', 'objects', 'filament_g', 'hours', 'black_g', 'white_g', 'lightblue_g', 'darkblue_g', 'red_g', 'supports', 'filament_changes'])
    for row in summaries:
        fs = {f['color']:f['grams'] for f in row['materials']}
        writer.writerow([row['id'], len(row['parts']), f'{row["grams"]:.3f}', f'{row["seconds"]/3600:.4f}',
                         *[f'{fs.get(c,0):.3f}' for c in COLOR_LABEL], int(row['supports']), row['filament_changes']])
    (ROOT/'print-estimates.csv').write_text('\ufeff'+output.getvalue())
    lines = ['# 打印用料与耗时', '', 'X2D · 0.4 mm · PLA · 0.20 mm。数值来自最终保存的 3MF 独立重开切片。', '',
             '| 范围 | 盘数 | 用料 | 切片预计耗时 |', '|---|---:|---:|---:|',
             f'| 完整装配件 | {len(production)} | {report["production_grams"]:.1f} g | {duration(report["production_seconds"])} |',
             f'| 接头试片 | 1 | {report["test_grams"]:.1f} g | {duration(report["test_seconds"])} |',
             f'| **合计** | **{len(summaries)}** | **{report["total_grams"]:.1f} g** | **{duration(report["total_seconds"])}** |', '',
             '| PLA 颜色 | 含试片用量 |', '|---|---:|']
    lines += [f'| {COLOR_LABEL[c]} | {colors[c]:.1f} g |' for c in COLOR_LABEL]
    lines += ['', '总量采用 `total_used_g`，包含切片器计入的支撑、换色及擦料用量。耗时采用 `total_predication`；不含人工换盘、冷却取件、修整和装配。', '',
              '按全新打印整套计算，含 29 个可复用原柱件；如果已有足量合适的柱件，可跳过第 29 号盘（原柱件），其切片估算单列在下面。', '',
              '| 盘号与内容 | 件数 | 用料 g | 耗时 | 支撑 |', '|---|---:|---:|---:|---|']
    lines += [f'| [{r["id"]}]({r["project"]}) | {len(r["parts"])} | {r["grams"]:.1f} | {duration(r["seconds"])} | {"有" if r["supports"] else "无"} |' for r in summaries]
    (ROOT/'打印用料与耗时.md').write_text('\n'.join(lines)+'\n')
    contact_sheet(summaries)
    bundle = ROOT/'parking-lot-v1-X2D-3mf.zip'
    files = []
    for directory in ('3mf', 'profiles', 'results'):
        files.extend(f for f in (ROOT/directory).rglob('*') if f.is_file())
    files.extend(ROOT/name for name in ('README.md', '装配说明.md', '打印用料与耗时.md', 'summary.json',
                  'plate-plan.json', 'parts.json', 'geometry-validation.json', 'print-estimates.csv', 'plate-overview.png',
                  'parking-lot-v1-print-parts.FCStd', 'assembly-plan.svg'))
    with ZipFile(bundle, 'w', ZIP_DEFLATED) as z:
        for file in files:
            z.write(file, str(file.relative_to(ROOT)))
    assert ZipFile(bundle).testzip() is None
    print(json.dumps({k:report[k] for k in ('status','plate_count','production_print_parts','total_grams','total_seconds','filament_grams')}, ensure_ascii=False), flush=True)


if __name__=='__main__':
    main()
