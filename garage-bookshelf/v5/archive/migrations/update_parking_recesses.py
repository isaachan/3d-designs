# Frozen v4 source; use v5/tools or the migrated studies.
if __name__ == '__main__':
    raise SystemExit('Historical entry disabled; see v5/README.md and archive/README.md')

"""Apply the approved 1.6 mm drop-in parking interface to current formal CAD.

Incremental retrofit only: preserve the F joints, removable lettering, slogan
and existing R3 features. Validate a separate candidate before replacing CAD.
No STL, STEP, 3MF, slicer setting or print project is generated or modified.
"""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, '/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as App
import Part

from assembly import global_shape
from parameters import PARAMETERS, evaluate, set_value
from parking_recesses import LAYOUTS, add_recesses, add_interface_sample, center_x

EXPECTED_SHA256 = '2a3f10a9a4c7d0544a9b2cfe2b4e5dfd48f4dd970dbd66d1bd2bd66c1b9191ce'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sync_parameters(doc):
    sheet = doc.DesignParameters
    row = max(int(c.lstrip('ABCDEFGHIJKLMNOPQRSTUVWXYZ')) for c in sheet.getNonEmptyCells())+1
    for alias, value, note in PARAMETERS:
        try:
            cell = sheet.getCellFromAlias(alias)
        except (ValueError, RuntimeError):
            cell = ''
        if cell:
            if alias not in ('DeckThickness', 'DeckFirstZ'):
                continue
            r = int(cell[1:])
        else:
            r = row
            row += 1
            sheet.set(f'A{r}', alias)
            sheet.setAlias(f'B{r}', alias)
        sheet.set(f'B{r}', value)
        sheet.set(f'C{r}', note)
        sheet.set(f'D{r}', 'derived' if value.startswith('=') else 'input')
    doc.recompute()
    for alias, expected in [('DeckThickness', 6.6), ('DeckFirstZ', 64.4),
        ('SegmentHeight', 56.4), ('PinLength', 9.6), ('TopSegmentHeight', 33)]:
        assert abs(evaluate(doc, alias)-expected) < 1e-6, alias


def valid(doc):
    bodies = [o for o in doc.Objects if o.TypeId == 'PartDesign::Body']
    for body in bodies:
        assert body.Shape.isValid() and len(body.Shape.Solids) == 1, body.Name
        assert body.Tip and not body.Tip.Shape.isNull(), body.Name
    sketches = [o for o in doc.Objects if o.TypeId == 'Sketcher::SketchObject']
    assert all(s.FullyConstrained for s in sketches), [s.Name for s in sketches if not s.FullyConstrained]
    errors = [(o.Name, list(o.State)) for o in doc.Objects
              if any(s in o.State for s in ('Invalid', 'Error', 'RecomputeFailed'))]
    assert not errors, errors
    assert not any(o.TypeId in ('Part::Feature', 'PartDesign::Feature', 'Mesh::Feature') for o in doc.Objects)
    return dict(bodies=len(bodies), fully_constrained_sketches=len(sketches),
                all_bodies_single_valid_solids=True, invalid_objects=errors)


def floor_height(shape, x, y, upper=10):
    ray = Part.makeLine(App.Vector(x, y, -1), App.Vector(x, y, upper))
    section = shape.common(ray)
    return max(v.Point.z for v in section.Vertexes)


def verify(doc, original, original_global, original_parameters):
    checks = valid(doc)
    all_bodies = [b for b in doc.Objects if b.TypeId == 'PartDesign::Body']
    shapes = {b.Name: global_shape(b) for b in all_bodies}
    sample_name = 'parking_tray_interface_Body'
    actual = {n: s for n, s in shapes.items() if n != sample_name}
    modified = {n+'_Body' for n in LAYOUTS}
    modified.update(f'column_{n}_segment_{level}_Body' for n in range(1, 5) for level in (1, 2, 3))
    unchanged = []
    for name, before in original.items():
        if name in modified:
            continue
        after = doc.getObject(name).Shape
        difference = before.cut(after).Volume+after.cut(before).Volume
        assert difference < 1e-6, (name, difference)
        difference_global = original_global[name].cut(actual[name]).Volume+actual[name].cut(original_global[name]).Volume
        assert difference_global < 1e-6, (name, difference_global)
        unchanged.append(name)
    print('CHECKED preserved bodies', len(unchanged), flush=True)
    pairs = []
    for a, b in itertools.combinations(shapes, 2):
        if shapes[a].BoundBox.intersect(shapes[b].BoundBox):
            overlap = shapes[a].common(shapes[b]).Volume
            assert overlap < .01, (a, b, overlap)
            pairs.append(dict(a=a, b=b, overlap_mm3=overlap))
    print('CHECKED all assembly interference', len(pairs), flush=True)
    holes = [(evaluate(doc, x), evaluate(doc, y)) for x, y in
             [('ColumnInset', 'ColumnInset'), ('ColumnX2', 'ColumnInset'),
              ('ColumnInset', 'ColumnY2'), ('ColumnX2', 'ColumnY2')]]
    floor_checks, contacts, lower_paths = [], [], []
    for source, count in LAYOUTS.items():
        base = source == 'module_1'
        body = doc.getObject(source+'_Body')
        top = evaluate(doc, 'BaseThickness' if base else 'DeckThickness')
        origin = body.getGlobalPlacement().Base
        shift = evaluate(doc, 'DeckEdgeGap') if base else 0
        centers = [(evaluate(doc, center_x(count, i))+shift,
                    evaluate(doc, 'ParkingCenterY')+shift) for i in range(count)]
        heights = [floor_height(body.Shape, x, y) for x, y in centers]
        assert all(abs(h-(top-1.6)) < 1e-6 for h in heights)
        assert body.TrayRecessCount == count
        assert any(o.TypeId == 'PartDesign::Chamfer' and 'ParkingTray' in o.Name for o in body.Group)
        floor_checks.append(dict(part=source, recess_count=count,
            recess_depth_from_nominal_top_mm=1.6, floor_thickness_mm=top-1.6,
            local_centers_xy_mm=centers, measured_floor_height_mm=heights,
            flat_bottom=True, entry_chamfer_mm=.2))
        if base:
            # All removed material must stay inside the small parking zone,
            # leaving F mating faces and the rear wall geometrically exact.
            removed = original[body.Name].cut(body.Shape)
            keep = Part.makeBox(185, 140, 9, App.Vector(20, 20, 0))
            assert removed.cut(keep).Volume < 1e-6
            assert body.Shape.cut(original[body.Name]).Volume < 1e-6
            continue
        level = int(source.rsplit('_', 1)[1])
        assert abs(body.Shape.BoundBox.ZLength-6.6) < 1e-6
        assert abs(origin.z+6.6-(71+63*(level-1))) < 1e-6
        for n, (cx, cy) in enumerate(holes, 1):
            local_x, local_y = cx-evaluate(doc, 'DeckEdgeGap'), cy-evaluate(doc, 'DeckEdgeGap')
            slab = Part.makeCylinder(10, .05, App.Vector(local_x, local_y, 0))
            old_area = original[body.Name].common(slab).Volume/.05
            new_area = body.Shape.common(slab).Volume/.05
            assert abs(old_area-new_area) < 1e-5
            contacts.append(dict(layer=level, column=n, bearing_area_mm2=new_area,
                                 unchanged_from_source=True))
        fixed = [actual[f'column_{n}_segment_{level}_Body'] for n in range(1, 5)]
        fixed += [actual['module_1_Body'], actual['module_2_Body']]
        for dz in (12, 8, 3, 0):
            moved = actual[body.Name].copy()
            moved.translate(App.Vector(0, 0, dz))
            overlap = sum(moved.common(s).Volume for s in fixed)
            assert overlap < .01, (source, dz, overlap)
            lower_paths.append(dict(layer=level, lift_mm=dz, overlap_mm3=overlap))
    print('CHECKED recess floors, supports and deck assembly paths', flush=True)
    # Test the actual editable sample against every receiving pocket and the
    # full furniture during lift and front removal, not just nominal rectangles.
    sample = doc.getObject(sample_name).Shape.copy()
    tray_paths = []
    for receiver in floor_checks:
        body = doc.getObject(receiver['part']+'_Body')
        origin = body.getGlobalPlacement().Base
        for i, ((x, y), h) in enumerate(zip(receiver['local_centers_xy_mm'], receiver['measured_floor_height_mm']), 1):
            for dz, dy in ((0, 0), (1.8, 0), (1.8, -10), (1.8, -45), (1.8, -90)):
                moved = sample.copy()
                moved.translate(App.Vector(origin.x+x, origin.y+y+dy, origin.z+h+dz))
                overlaps = []
                for name, fixed in actual.items():
                    if moved.BoundBox.intersect(fixed.BoundBox):
                        volume = moved.common(fixed).Volume
                        if volume > .01:
                            overlaps.append((name, volume))
                assert not overlaps, (receiver['part'], i, dz, dy, overlaps)
                tray_paths.append(dict(part=receiver['part'], bay=i, lift_mm=dz,
                                      front_translation_mm=dy, interference=[]))
    print('CHECKED tray fit and front removal', len(tray_paths), flush=True)
    for level in (1, 2, 3):
        for col in range(1, 5):
            body = doc.getObject(f'column_{col}_segment_{level}_Body')
            assert abs(body.Shape.BoundBox.ZLength-66) < 1e-6
    assert all(abs(doc.getObject(f'column_{n}_segment_4_Body').getGlobalPlacement().Base.z-197) < 1e-6 for n in range(1, 5))
    assert evaluate(doc, 'FitClearance') == original_parameters['FitClearance']
    assert doc.side_cartridge_Body.EngravedSlogan == 'HORSEPOWER LEFT, BRAINPOWER RIGHT'
    bounds = Part.makeCompound(list(actual.values())).BoundBox
    previous_bounds = Part.makeCompound(list(original_global.values())).BoundBox
    assert all(abs(a-b) < 1e-6 for a, b in zip(
        [bounds.XMin, bounds.YMin, bounds.ZMin, bounds.XMax, bounds.YMax, bounds.ZMax],
        [previous_bounds.XMin, previous_bounds.YMin, previous_bounds.ZMin,
         previous_bounds.XMax, previous_bounds.YMax, previous_bounds.ZMax]))
    return dict(native=checks, unchanged_bodies=unchanged,
        updated_existing_bodies=sorted(modified), recesses=floor_checks,
        total_recesses=sum(r['recess_count'] for r in floor_checks),
        assembly_overlaps=pairs, collar_contacts=contacts,
        deck_lowering_paths=lower_paths, tray_insertion_and_removal_paths=tray_paths,
        original_parameters_mm=original_parameters,
        parameters_mm={k: evaluate(doc, k) for k in
            ['DeckThickness', 'DeckFirstZ', 'DeckZ2', 'DeckZ3', 'SegmentHeight',
             'PinLength', 'TopSegmentHeight', 'ParkingRecessDepth', 'ParkingRecessWidth',
             'ParkingRecessLength', 'TraySideClearance', 'ParkingEntryChamfer']},
        outer_dimensions_mm=[bounds.XLength, bounds.YLength, bounds.ZLength],
        outer_envelope_unchanged_from_source=True,
        original_F_interfaces_and_removable_signs_preserved=True,
        sample_has_vehicle_wheel_restraints=False)


def run(cad, backup, report):
    cad, backup, report = map(Path, (cad, backup, report))
    assert sha(cad) == EXPECTED_SHA256, 'Formal CAD changed since evaluated revision; inspect before applying.'
    backup.parent.mkdir(parents=True, exist_ok=True)
    if backup.exists():
        assert sha(backup) == EXPECTED_SHA256, 'Existing backup belongs to another revision.'
    else:
        shutil.copy2(cad, backup)
    doc = App.openDocument(str(cad))
    original = {b.Name: b.Shape.copy() for b in doc.Objects if b.TypeId == 'PartDesign::Body'}
    original_global = {b.Name: global_shape(b) for b in doc.Objects if b.TypeId == 'PartDesign::Body'}
    original_parameters = {k: evaluate(doc, k) for k in
        ['DeckThickness', 'DeckFirstZ', 'SegmentHeight', 'PinLength', 'FitClearance']}
    sync_parameters(doc)
    print('UPDATED parameters and 12 supporting column segments', flush=True)
    valid(doc)
    for source, count in LAYOUTS.items():
        add_recesses(doc.getObject(source+'_Body'), count, source == 'module_1')
        print('ADDED', source, count, 'recesses', flush=True)
    sample = add_interface_sample(doc)
    doc.recompute()
    result = verify(doc, original, original_global, original_parameters)
    snapshots = {b.Name: b.Shape.copy() for b in doc.Objects if b.TypeId == 'PartDesign::Body'}
    for alias, temporary, restored in [('TraySideClearance', '.35 mm', '.3 mm'),
                                        ('ParkingRecessDepth', '1.4 mm', '1.6 mm')]:
        set_value(doc, alias, temporary)
        valid(doc)
        set_value(doc, alias, restored)
        valid(doc)
    for name, before in snapshots.items():
        after = doc.getObject(name).Shape
        assert before.cut(after).Volume+after.cut(before).Volume < 1e-5, name
    result['parameter_round_trips'] = dict(side_clearance_0p3_0p35_0p3='passed',
                                          recess_depth_1p6_1p4_1p6='passed')
    candidate = report.parent/'parking-recesses-candidate.FCStd'
    doc.saveAs(str(candidate))
    from cad_view_style import preserve_views
    result['appearance'] = preserve_views(backup, candidate, doc,
        [name+'_Body' for name in LAYOUTS]+[sample.Name])
    App.closeDocument(doc.Name)
    reopened = App.openDocument(str(candidate))
    valid(reopened)
    for name, before in snapshots.items():
        after = reopened.getObject(name).Shape
        assert before.cut(after).Volume+after.cut(before).Volume < 1e-5, name
    App.closeDocument(reopened.Name)
    assert sha(cad) == EXPECTED_SHA256
    candidate.replace(cad)
    result.update(status='passed', backup=str(backup), original_sha256=sha(backup),
        cad=str(cad), cad_sha256=sha(cad), saved_reopened=True,
        three_mf_modified=False, STEP_STL_regenerated=False,
        physical_fit_and_vehicle_wheel_restraints='not_verified')
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print('PASS', report, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cad', type=Path, default=ROOT/'garage-bookshelf-v4-assembly.FCStd')
    parser.add_argument('--backup', type=Path, default=ROOT/'backups/2026-10-25-before-parking-recesses.FCStd')
    parser.add_argument('--report', type=Path, default=ROOT/'reports/parking-recesses-validation.json')
    args = parser.parse_args()
    run(args.cad, args.backup, args.report)
