"""Read current formal CAD and make one temporary deck/tray review project.

Run with /Applications/FreeCAD.app/Contents/Resources/bin/python.
The formal CAD and the historical print exports are never saved or rebuilt.
"""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import xml.etree.ElementTree as ET
from zipfile import ZipFile
from zipfile import ZIP_DEFLATED

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / 'src'))
from garage_bookshelf.paths import CAD, PROFILES, ROOT, TMP, study_directory
OUT = study_directory('parking-tray-fit')
sys.path.insert(0, '/Applications/FreeCAD.app/Contents/Resources/lib')

import FreeCAD as App
import Mesh
import MeshPart
import numpy as np

from garage_bookshelf.printing.threemf import project_bounds
from garage_bookshelf.printing.bambu import read_settings, run_cli
from garage_bookshelf.parameters import evaluate
from garage_bookshelf.parking.recesses import center_x
from garage_bookshelf.rendering.software import render, saved_colors, triangles


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    cad = CAD
    before = sha(cad)
    doc = App.openDocument(str(cad))
    deck_body = doc.garage_deck_2_Body
    tray_body = doc.parking_tray_interface_Body
    deck, tray = deck_body.Shape.copy(), tray_body.Shape.copy()
    assert deck_body.TrayRecessCount == 3
    assert not tray_body.VehicleRetentionComplete
    assert abs(evaluate(doc, 'DeckThickness') - 6.6) < 1e-6
    assert abs(evaluate(doc, 'ParkingRecessDepth') - 1.6) < 1e-6

    mesh_records = []
    files = []
    for name, shape, expected in (
        ('3bay-parking-deck-301-303', deck, [195.6, 158.6, 6.6]),
        ('parking-tray-foot-with-pull-tab', tray, [40, 83, 3.2]),
    ):
        assert shape.isValid() and len(shape.Solids) == 1, name
        mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=.02,
                                      AngularDeflection=.12, Relative=False)
        bb = mesh.BoundBox
        mesh.translate(-bb.XMin, -bb.YMin, -bb.ZMin)
        file = OUT / (name + '.stl')
        mesh.write(str(file))
        check = Mesh.Mesh(str(file))
        assert check.isSolid() and not check.hasNonManifolds(), name
        assert len(check.getSeparateComponents()) == 1, name
        bb = check.BoundBox
        dims = [bb.XLength, bb.YLength, bb.ZLength]
        assert all(abs(a-b) < .002 for a, b in zip(dims, expected)), dims
        volume_error = abs(abs(check.Volume)-shape.Volume)/shape.Volume
        assert volume_error < .001, (name, volume_error)
        mesh_records.append(dict(file=file.name, dimensions_mm=dims,
            valid_single_solid=True, watertight=True, non_manifold=False,
            triangles=check.CountFacets, sha256=sha(file),
            relative_mesh_volume_error=volume_error))
        files.append(file)
        print('EXPORTED', name, dims, flush=True)

    # Check the actual current shapes at all three recesses, including lift-out.
    fit = []
    floor_z = evaluate(doc, 'DeckThickness-ParkingRecessDepth')
    cy = evaluate(doc, 'ParkingCenterY')
    for index in range(3):
        cx = evaluate(doc, center_x(3, index))
        for lift, front in ((0, 0), (1.8, 0), (1.8, -10),
                            (1.8, -45), (1.8, -90)):
            moved = tray.copy()
            moved.translate(App.Vector(cx, cy+front, floor_z+lift))
            overlap = deck.common(moved).Volume
            assert overlap < .001, (index, lift, front, overlap)
            fit.append(dict(bay=301+index, lift_mm=lift,
                forward_translation_mm=front, interference_mm3=overlap))
        seated = tray.copy()
        # A 0.01 mm penetration probe measures support without relying on
        # OCC returning coincident touching faces in a solid intersection.
        seated.translate(App.Vector(cx, cy, floor_z-.01))
        contact = deck.common(seated).Volume/.01
        assert contact > 3000, (index, contact)

    # Actual CAD face geometry; the sample is seated in the middle bay.
    colors = saved_colors(cad)
    # Temporary display colour makes the flush black-on-black interface visible.
    colors[tray_body.Tip.Name] = [(.92, .58, .16)]*len(tray.Faces)
    deck_points, deck_paint = triangles(doc, colors, ['garage_deck_2'], local=True)
    tray_points, tray_paint = triangles(doc, colors, ['parking_tray_interface'], local=True)
    tray_points += np.array([evaluate(doc, center_x(3, 1)), cy, floor_z])
    preview = render(np.concatenate([deck_points, tray_points]),
        np.concatenate([deck_paint, tray_paint]), OUT/'seated-preview.png',
        [-.65, -1.9, 3.2], width=1500, height=1100)
    App.closeDocument(doc.Name)
    assert sha(cad) == before, 'Formal CAD changed during export'
    print('PASS three recesses and tray lift-out; rendered seated preview', flush=True)

    profiles = PROFILES
    project = OUT/'TEMP-3bay-deck-and-one-parking-tray.3mf'
    TMP.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='garage-v5-tray-review-', dir=TMP) as scratch:
        work = Path(scratch)
        arranged = work/'arranged.3mf'
        run_cli(['--load-settings',
            f'{profiles}/X2D-0.4-standard-machine.json;{profiles}/PLA-0.20-process.json',
            '--load-filaments', profiles/'PLA-black.json',
            '--orient', '0', '--arrange', '1', '--export-3mf', arranged, *files],
            work/'export-state', OUT/'export.log')
        # The default arrangement uses only a 2 mm gap. Open it to 10 mm to
        # leave room for both optional 4 mm brims, then let Studio re-export
        # the project and refresh thumbnails with the saved placement.
        initial_bounds = project_bounds(arranged)
        gap = initial_bounds[0]['min_mm'][1]-initial_bounds[1]['max_mm'][1]
        assert gap >= 0, initial_bounds
        shift = max(0, (10-gap)/2)
        with ZipFile(arranged) as z:
            archive = {n: z.read(n) for n in z.namelist()}
        ns = 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
        ET.register_namespace('', ns)
        ET.register_namespace('p', 'http://schemas.microsoft.com/3dmanufacturing/production/2015/06')
        model = ET.fromstring(archive['3D/3dmodel.model'])
        items = model.findall('{'+ns+'}build/{'+ns+'}item')
        assert len(items) == 2
        for item, dy in zip(items, (shift, -shift)):
            matrix = list(map(float, item.attrib['transform'].split()))
            matrix[10] += dy
            item.set('transform', ' '.join(f'{v:.12g}' for v in matrix))
        archive['3D/3dmodel.model'] = ET.tostring(model, encoding='utf-8', xml_declaration=True)
        with ZipFile(arranged, 'w', ZIP_DEFLATED) as z:
            for name, value in archive.items():
                z.writestr(name, value)
        run_cli(['--orient', '0', '--arrange', '0', '--export-3mf', project, arranged],
                work/'layout-state', OUT/'layout-export.log')
        settings = read_settings(project, 'black', False)
        assert settings['enable_support'] == '0'
        bounds = project_bounds(project)
        assert len(bounds) == 2, bounds
        # The exported transforms must preserve size, not shrink either object.
        for bound, mesh in zip(bounds, mesh_records):
            size = [b-a for a, b in zip(bound['min_mm'], bound['max_mm'])]
            assert all(abs(a-b) < .002 for a, b in
                zip(sorted(size[:2]), sorted(mesh['dimensions_mm'][:2]))), size
            assert abs(size[2]-mesh['dimensions_mm'][2]) < .002, size
        assert any(bounds[0]['max_mm'][axis]+8 <= bounds[1]['min_mm'][axis]+.01
            or bounds[1]['max_mm'][axis]+8 <= bounds[0]['min_mm'][axis]+.01
            for axis in (0, 1)), 'Need at least 8 mm between object bounds'
        with ZipFile(project) as z:
            (OUT/'plate-preview.png').write_bytes(z.read('Metadata/plate_1.png'))
            assert not any(n.endswith('.gcode') for n in z.namelist())
        print('EXPORTED 3MF; reopening saved project for offline slicing', flush=True)
        sliced = work/'sliced'
        sliced.mkdir()
        run_cli(['--orient', '0', '--arrange', '0', '--outputdir', sliced,
                 '--slice', '0', project], work/'reload-state', OUT/'slice.log')
        result = json.loads((sliced/'result.json').read_text())
        (OUT/'slice-result.json').write_text(json.dumps(result, indent=2)+'\n')
        assert result['return_code'] == 0 and len(result['sliced_plates']) == 1, result
        plate = result['sliced_plates'][0]
        assert len(plate['objects']) == 2 and not plate['warning_message'], plate
        assert plate['filament_change_times'] == 0
        assert len(plate['filaments']) == 1 and plate['filaments'][0]['total_used_g'] > 0
        assert abs(result['layer_height']-.2) < 1e-6

    assert sha(cad) == before
    report = dict(status='passed', source_cad=str(cad), cad_sha256=before,
        formal_cad_unchanged=True, current_formal_solids_used=True,
        project=project.name, sha256=sha(project), object_count=2, plate_count=1,
        mesh_exports=mesh_records, settings=settings, object_bounds=bounds,
        recess_depth_mm=1.6, floor_thickness_mm=5, foot_body_mm=[40,80,2],
        foot_with_pull_tab_mm=[40,83,3.2], side_clearance_mm=.3,
        tray_seated_base_protrusion_mm=.4, geometric_fit_paths=fit,
        saved_3mf_reopened_and_sliced=True, slice_profile_overrides=False,
        warnings=plate['warning_message'], estimated_seconds=plate['total_predication'],
        estimated_filament_g=plate['filaments'][0]['total_used_g'],
        preview=preview, preview_tray_colour='amber for identification only',
        vehicle_specific_wheel_restraints_included=False,
        physical_print_and_fit_tested=False, gcode_delivered=False)
    (OUT/'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    minutes = round(plate['total_predication']/60)
    grams = plate['filaments'][0]['total_used_g']
    (OUT/'README.md').write_text(f'''# 临时三车位层板＋停车托座

`{project.name}`：1盘、2个独立对象，各1件。

- 层板直接取自当前正式CAD的 `garage_deck_2_Body`：301–303三车位，195.6 × 158.6 × 6.6 mm，含三处1.6 mm深浅槽、取放缺口及现有凹刻停车图案。
- 托座取自 `parking_tray_interface_Body`：40 × 80 × 2 mm通用底脚，带取放耳后包络40 × 83 × 3.2 mm。落座后基板高出板面0.4 mm；名义单边间隙0.3 mm。
- 托座仅含通用底脚和取放耳，未包含车型轮胎夹，不能单独固定车轮。
- 3MF内层板与托座分别底面贴床，槽口和取放凸起朝上，自动排在同一盘。
- X2D、0.4 mm、黑色PLA、纹理PEI、0.20 mm层高、4圈墙、25%填充、4 mm自动brim、无支撑。图案为实体凹刻，CAD填色和三色外观面未作为多色耗材导出。
- 保存后已重新加载3MF离线切片：2对象、1盘、无模型警告。估算{minutes}分钟、{grams:.1f} g；未实物打印。

`seated-preview.png` 显示同一托座落在302号车位的CAD效果；`plate-preview.png` 显示3MF内的实际打印排盘。装配预览将托座临时显示为橙色以便辨认，3MF使用单一黑色PLA。

正式CAD及既有打印文件未修改。源文件与输出哈希、网格检查、三个槽的落座与抬出路径见 `validation.json`。

复现：`/Applications/FreeCAD.app/Contents/Resources/bin/python build_review.py`
''')
    print(f'PASS {project}; {minutes} min; {grams:.1f} g; source CAD unchanged', flush=True)


if __name__ == '__main__':
    main()
