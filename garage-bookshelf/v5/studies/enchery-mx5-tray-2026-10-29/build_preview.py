"""One rough MX-5 tray, using the formal CAD's unchanged parking interface.

Run with FreeCAD's Python. Generated artifacts go to build/studies/ only.
"""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from zipfile import ZipFile

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / 'src'))
sys.path.insert(0, '/Applications/FreeCAD.app/Contents/Resources/lib')

import FreeCAD as App
import Mesh
import MeshPart
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from garage_bookshelf.geometry.features import pad
from garage_bookshelf.geometry.sketches import loops
from garage_bookshelf.parameters import evaluate
from garage_bookshelf.parking.recesses import LAYOUTS, center_x
from garage_bookshelf.paths import CAD, PROFILES, TMP, study_directory
from garage_bookshelf.printing.bambu import read_settings, run_cli
from garage_bookshelf.printing.threemf import project_bounds
from garage_bookshelf.rendering.software import render, triangles

OUT = study_directory('enchery-mx5-tray-2026-10-29')
STEM = 'enchery-1-65-mazda-mx5-parking-tray-preview'
PARAMETERS = {
    'VehicleLength': (61.2, 'User supplied nominal vehicle length'),
    'VehicleWidth': (27.1, 'User supplied nominal vehicle width'),
    'VehicleHeight': (19.3, 'User supplied nominal vehicle height'),
    'EstimatedWheelbase': (36.0, 'Preview assumption; not measured'),
    'EstimatedTrack': (23.0, 'Wheel centre spacing; preview assumption'),
    'EstimatedTireDiameter': (9.0, 'Preview assumption; not measured'),
    'EstimatedTireWidth': (3.0, 'Preview assumption; not measured'),
    'SideClearance': (1.0, 'Clearance each side of nominal body envelope'),
    'RailThickness': (1.6, 'Low outer side guide thickness'),
    'RailHeight': (1.4, 'Side guide height above the existing base'),
    'RailLength': (56.0, 'Side guides leave both ends open'),
    'StopWidth': (5.6, 'Width of each wheel stop across the tire'),
    'StopSetback': (5.1, 'Axle centre to inner edge of each wheel stop'),
    'StopDepth': (1.8, 'Depth of the sloping stop'),
    'StopHeight': (1.2, 'Wheel stop height above the existing base'),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_model(base_shape):
    doc = App.newDocument('MX5ParkingTrayPreview')
    params = doc.addObject('Spreadsheet::Sheet', 'DesignParameters')
    params.set('A1', '0 mm')
    params.setAlias('A1', 'Zero')
    params.set('A2', '2 mm')
    params.setAlias('A2', 'TrayPlateThickness')
    vehicle = doc.addObject('App::FeaturePython', 'VehiclePreview')
    vehicle.Label = 'MX-5 preview dimensions - wheel positions estimated'
    for name, (value, description) in PARAMETERS.items():
        vehicle.addProperty('App::PropertyLength', name, 'Preview dimensions', description)
        setattr(vehicle, name, value)
    vehicle.addProperty('App::PropertyString', 'FitStatus', 'Preview dimensions')
    vehicle.FitStatus = 'Visual preview: low wheel stops, no snap-fit or tested retention'
    body = doc.addObject('PartDesign::Body', 'mx5_tray_Body')
    body.Label = 'ENCHERY 1:65 Mazda MX-5 - rough parking tray'
    base = body.newObject('PartDesign::Feature', 'OriginalParkingInterface')
    base.Label = 'Original 40 x 80 x 2 mm foot and pull tab'
    base.Shape = base_shape
    base.addProperty('App::PropertyString', 'SourceCAD', 'Source')
    base.SourceCAD = str(CAD)
    body.Tip = base
    doc.recompute()

    # Native editable sketch and pad for two low side guides.
    polygons = []
    inner = 'VehiclePreview.VehicleWidth/2+VehiclePreview.SideClearance'
    for sign in (-1, 1):
        a = f'({sign})*({inner})'
        b = f'({sign})*({inner}+VehiclePreview.RailThickness)'
        x0, x1 = (b, a) if sign < 0 else (a, b)
        y0, y1 = '-VehiclePreview.RailLength/2', 'VehiclePreview.RailLength/2'
        polygons.append([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    rails_sketch = loops(body, 'Sketch_LowSideGuides', polygons,
                         offset=('Zero', 'Zero', 'TrayPlateThickness'))
    rails = pad(body, 'Pad_LowSideGuides', rails_sketch, 'VehiclePreview.RailHeight')

    # Each YZ sketch contains four triangular ramps, two per estimated axle.
    # They rise toward each wheel, with generous space around its nominal tyre.
    polygons = []
    for axle in (-1, 1):
        cy = f'({axle})*VehiclePreview.EstimatedWheelbase/2'
        for direction in (-1, 1):
            inner_y = f'({cy})+({direction})*VehiclePreview.StopSetback'
            outer_y = f'({inner_y})+({direction})*VehiclePreview.StopDepth'
            floor, top = 'TrayPlateThickness-0.02 mm', 'TrayPlateThickness+VehiclePreview.StopHeight'
            points = ([(inner_y, floor), (outer_y, floor), (inner_y, top)]
                      if direction > 0 else
                      [(outer_y, floor), (inner_y, floor), (inner_y, top)])
            polygons.append(points)
    for name, sign in (('Left', -1), ('Right', 1)):
        sketch = loops(body, 'Sketch_' + name + 'WheelStops', polygons,
                       orientation='YZ',
                       offset=(f'({sign})*VehiclePreview.EstimatedTrack/2-VehiclePreview.StopWidth/2',
                               'Zero', 'Zero'))
        pad(body, 'Pad_' + name + 'WheelStops', sketch, 'VehiclePreview.StopWidth')
    doc.recompute()
    assert body.Shape.isValid() and len(body.Shape.Solids) == 1
    assert abs(body.Shape.common(base_shape).Volume - base_shape.Volume) < 1e-5
    assert all(s.FullyConstrained for s in doc.Objects if s.TypeId == 'Sketcher::SketchObject')
    return doc, body


def top_diagram():
    # This schematic is separate from the printable mesh. Dashed blue outline
    # is the user supplied car envelope; four grey tyres are only assumptions.
    image = Image.new('RGB', (1000, 1220), '#f7f8fa')
    draw = ImageDraw.Draw(image)
    font_path = '/System/Library/Fonts/Supplemental/Arial.ttf'
    font = ImageFont.truetype(font_path, 25)
    small = ImageFont.truetype(font_path, 20)
    scale, cx, cy = 11, 500, 620

    def rect(x0, y0, x1, y1):
        return [cx+x0*scale, cy-y1*scale, cx+x1*scale, cy-y0*scale]

    draw.text((60, 40), 'ENCHERY 1:65 Mazda MX-5 / rough tray', fill='#202b36', font=font)
    draw.rounded_rectangle(rect(-20, -40, 20, 40), radius=22, fill='#d4d9de', outline='#28323c', width=3)
    draw.rectangle(rect(-5, -43, 5, -39.5), fill='#aab2bb', outline='#28323c', width=2)
    for sign in (-1, 1):
        x0, x1 = (14.55, 16.15) if sign > 0 else (-16.15, -14.55)
        draw.rectangle(rect(x0, -28, x1, 28), fill='#4f5d6b')
    for x in (-11.5, 11.5):
        for y in (-18, 18):
            draw.rounded_rectangle(rect(x-1.5, y-4.5, x+1.5, y+4.5), radius=9,
                                   fill='#979fa8', outline='#59616a', width=2)
            for sign in (-1, 1):
                low, high = sorted((y+sign*5.1, y+sign*6.9))
                draw.rectangle(rect(x-2.8, low, x+2.8, high), fill='#313d49')
    x0, y0, x1, y1 = rect(-27.1/2, -61.2/2, 27.1/2, 61.2/2)
    for y in (y0, y1):
        for x in np.arange(x0, x1, 15):
            draw.line((x, y, min(x+8, x1), y), fill='#1677b8', width=3)
    for x in (x0, x1):
        for y in np.arange(y0, y1, 15):
            draw.line((x, y, x, min(y+8, y1)), fill='#1677b8', width=3)
    draw.text((cx-120, cy-40*scale-42), '40 mm base width', fill='#263440', font=small)
    draw.text((cx+20*scale+26, cy-50), '80 mm', fill='#263440', font=small)
    draw.text((60, 1120), 'Blue dashes: 61.2 x 27.1 mm nominal car envelope', fill='#1677b8', font=small)
    draw.text((60, 1154), 'Wheelbase 36 / track 23 / tire diameter 9 mm: estimated', fill='#59616a', font=small)
    draw.text((60, 1184), 'Diagram only: car and tires are absent from the 3MF.', fill='#59616a', font=small)
    image.save(OUT / 'top-fit-preview.png')


def main():
    source_hash = sha(CAD)
    source = App.openDocument(str(CAD))
    base = source.parking_tray_interface_Body.Shape.copy()
    doc, body = build_model(base)
    shape = body.Shape.copy()

    # Confirm current formal parking slots still accept the unchanged foot.
    fit = []
    for name, count in LAYOUTS.items():
        is_base = name == 'module_1'
        shift = 'DeckEdgeGap+' if is_base else ''
        floor = ('BaseThickness' if is_base else 'DeckThickness') + '-ParkingRecessDepth'
        for index in range(count):
            moved = shape.copy()
            moved.translate(App.Vector(evaluate(source, shift + center_x(count, index)),
                                       evaluate(source, shift + 'ParkingCenterY'),
                                       evaluate(source, floor)))
            overlap = source.getObject(name + '_Body').Shape.common(moved).Volume
            assert overlap < .001, (name, index, overlap)
            fit.append(dict(floor=name, index=index, interference_mm3=overlap))
    App.closeDocument(source.Name)
    print('PASS native CAD, single solid and fit in all ten existing parking slots', flush=True)

    cad = OUT / (STEM + '.FCStd')
    doc.saveAs(str(cad))
    colour = (.30, .34, .39)
    points, paint = triangles(doc, {body.Tip.Name: [colour]}, ['mx5_tray'], local=True)
    render(points, paint, OUT / 'tray-preview.png', [-1.1, -1.65, 2.4], width=1400, height=1200)
    top_diagram()

    mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=.02, AngularDeflection=.12, Relative=False)
    bb = mesh.BoundBox
    mesh.translate(-bb.XMin, -bb.YMin, -bb.ZMin)
    stl = OUT / (STEM + '.stl')
    mesh.write(str(stl))
    check = Mesh.Mesh(str(stl))
    assert check.isSolid() and not check.hasNonManifolds()
    assert len(check.getSeparateComponents()) == 1
    dimensions = [check.BoundBox.XLength, check.BoundBox.YLength, check.BoundBox.ZLength]
    assert all(abs(a-b) < .002 for a, b in zip(dimensions, [40, 83, 3.4]))
    assert abs(abs(check.Volume)-shape.Volume)/shape.Volume < .001
    App.closeDocument(doc.Name)
    reopened = App.openDocument(str(cad))
    reopened.recompute()
    assert reopened.mx5_tray_Body.Shape.isValid()
    assert abs(reopened.mx5_tray_Body.Shape.Volume-shape.Volume) < 1e-5
    App.closeDocument(reopened.Name)
    print('PASS watertight single component STL and reopened editable CAD', flush=True)

    project = OUT / (STEM + '.3mf')
    TMP.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='mx5-tray-', dir=TMP) as scratch:
        work = Path(scratch)
        run_cli(['--load-settings',
                 f'{PROFILES}/X2D-0.4-standard-machine.json;{PROFILES}/PLA-0.20-process.json',
                 '--load-filaments', PROFILES / 'PLA-black.json', '--orient', '0',
                 '--arrange', '1', '--export-3mf', project, stl],
                work / 'export-state', OUT / 'export.log')
        settings = read_settings(project, 'black', False)
        bounds = project_bounds(project)
        assert len(bounds) == 1
        saved_dimensions = [b-a for a, b in zip(bounds[0]['min_mm'], bounds[0]['max_mm'])]
        assert all(abs(a-b) < .002 for a, b in zip(sorted(saved_dimensions), sorted(dimensions)))
        with ZipFile(project) as archive:
            (OUT / 'plate-preview.png').write_bytes(archive.read('Metadata/plate_1.png'))
            assert not any(name.endswith('.gcode') for name in archive.namelist())
        print('EXPORTED one-object 3MF; reopening and slicing saved file', flush=True)
        sliced = work / 'sliced'
        sliced.mkdir()
        run_cli(['--orient', '0', '--arrange', '0', '--outputdir', sliced, '--slice', '0', project],
                work / 'reload-state', OUT / 'slice.log')
        result = json.loads((sliced / 'result.json').read_text())
        (OUT / 'slice-result.json').write_text(json.dumps(result, indent=2) + '\n')
        assert result['return_code'] == 0 and len(result['sliced_plates']) == 1
        plate = result['sliced_plates'][0]
        assert len(plate['objects']) == 1 and not plate['warning_message']
        assert plate['filament_change_times'] == 0
        assert abs(result['layer_height']-.2) < 1e-6
        assert len(plate['filaments']) == 1 and plate['filaments'][0]['total_used_g'] > 0

    assert sha(CAD) == source_hash
    report = dict(status='passed', source_cad=str(CAD), source_cad_sha256=source_hash,
        formal_cad_unchanged=True, original_foot_preserved=True,
        car_dimensions_mm=[61.2, 27.1, 19.3], parameters={k:v[0] for k,v in PARAMETERS.items()},
        wheel_geometry_is_estimated=True, vehicle_retention_tested=False,
        dimensions_mm=dimensions, triangles=check.CountFacets,
        mesh_watertight=True, mesh_components=1, object_count=1, plate_count=1,
        vehicle_mesh_included=False, deck_mesh_included=False,
        current_slot_interference_checks=fit, settings=settings,
        reopened_and_sliced=True, warnings=plate['warning_message'],
        estimated_seconds=plate['total_predication'],
        estimated_filament_g=plate['filaments'][0]['total_used_g'],
        sha256={p.name:sha(p) for p in (cad, stl, project)})
    (OUT / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    minutes = round(report['estimated_seconds']/60)
    grams = report['estimated_filament_g']
    (OUT / 'README.md').write_text(f'''# ENCHERY 1:65 Mazda MX-5 停车托座预览

`{project.name}`：仅一个托座、一个对象、一盘，无层板和车模。

- 车模理论尺寸由用户给定：61.2 × 27.1 × 19.3 mm。
- 沿用正式 CAD 的 40 × 80 × 2 mm 圆角底脚及取放耳；总包络 40 × 83 × 3.4 mm。
- 两侧低挡高 1.4 mm，内净宽 29.1 mm；八个斜面轮挡高 1.2 mm。
- 轴距 36 mm、轮距 23 mm、轮胎直径 9 mm、宽 3 mm 均为视觉预览估算；轮挡宽松放置，未设计弹性卡扣，未实测夹持效果。
- `top-fit-preview.png` 中蓝色虚线是车模的理论长宽，灰色轮胎仅用于说明估算位置，均未放入 3MF。
- FreeCAD 文件保留原始底脚，并使用全约束草图和原生 Pad 添加侧挡与轮挡。`VehiclePreview` 中可编辑预览参数；原始底脚为正式 CAD 的形状快照。
- X2D、0.4 mm、黑色 PLA、0.20 mm 层高、4 圈墙、25% 填充、4 mm 自动 brim、无支撑。
- 已重开 CAD 并重算，检查封闭单连通网格、十个正式车位无干涉；已重新加载 3MF 切片，无模型警告。估算 {minutes} 分钟、{grams:.1f} g；未实物打印。
- 正式 CAD 哈希保持不变。详见 `validation.json`。

复现：用 FreeCAD Python 运行 `studies/enchery-mx5-tray-2026-10-29/build_preview.py --output build/<新目录>`。
''')
    print(f'PASS {project}; {minutes} min; {grams:.1f} g', flush=True)


if __name__ == '__main__':
    main()
