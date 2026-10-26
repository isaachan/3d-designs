"""Keep 2/3 of the posts' original exposed length above the main body.

Run ``import shorten_billboard_posts as m; m.run(App.ActiveDocument)`` in the
FreeCAD Python console. Do not rebuild the historical assembly from scratch.
"""
import hashlib
import json
import shutil
from pathlib import Path

import FreeCAD as App
import Part
from assembly import global_shape

ROOT = Path(__file__).resolve().parent
CAD = ROOT / 'garage-bookshelf-v4-assembly.FCStd'
BACKUP = ROOT / 'backups/2026-10-26-before-shorter-billboard-posts.FCStd'
REPORT = ROOT / 'reports/shorter-billboard-posts-validation.json'
CORRECTION_BACKUP = ROOT / 'backups/2026-10-26-before-exposed-post-correction.FCStd'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def difference(a, b):
    return a.cut(b).Volume + b.cut(a).Volume


def run(doc):
    assert App.GuiUp, 'Use the GUI to preserve all saved face colors.'
    import FreeCADGui as Gui
    assert Path(doc.FileName) == CAD
    sheet = doc.DesignParameters
    before_bottom = sheet.BillboardBottom.Value
    assert any(abs(before_bottom - z) < 1e-7 for z in (250, 300))
    original_exposed = 300 - 238
    target_bottom = sheet.OverallHeight.Value + original_exposed * 2 / 3
    move_z = target_bottom - before_bottom
    post_length = target_bottom - sheet.PostBottom.Value
    BACKUP.parent.mkdir(exist_ok=True)
    if not BACKUP.exists():
        assert abs(before_bottom - 300) < 1e-7
        shutil.copy2(CAD, BACKUP)
    if abs(before_bottom - 250) < 1e-7:
        assert not CORRECTION_BACKUP.exists(), 'Never overwrite the correction backup.'
        shutil.copy2(CAD, CORRECTION_BACKUP)
    bodies = [o for o in doc.Objects if o.TypeId == 'PartDesign::Body']
    original = {b.Name: global_shape(b) for b in bodies}
    moved = {'top_carrier_Body', 'hardware_screw_1_Body', 'hardware_nut_1_Body',
             'hardware_screw_2_Body', 'hardware_nut_2_Body'}
    styles = {b.Name: (tuple(b.ViewObject.ShapeColor), tuple(b.ViewObject.DiffuseColor))
              for b in bodies}
    doc.openTransaction('广告牌露出竖杆保留原来的2/3：62 → 41.333 mm')
    try:
        # Attach the removable plate, both text rows and its four metal parts to
        # the board height. The old file froze these at 302/332/304/331 mm.
        doc.top_carrier.setExpression('Placement.Base.z', 'DesignParameters.BillboardBottom + 2 mm')
        for number in (1, 2):
            for kind in ('screw', 'nut'):
                doc.getObject(f'hardware_{kind}_{number}').setExpression(
                    'Placement.Base.z', 'DesignParameters.BillboardBottom + 31 mm')
        text_sketches = [o for o in doc.top_carrier_Body.Group
                        if o.TypeId == 'Sketcher::SketchObject' and o.Name.startswith('Sketch_TextOutline')]
        assert len(text_sketches) == 20
        for obj in text_sketches:
            old = next(e for p, e in obj.ExpressionEngine if p == '.Placement.Base.z')
            if old.endswith(' - 302 mm'):
                obj.setExpression('Placement.Base.z', old.replace(
                    ' - 302 mm', ' - (DesignParameters.BillboardBottom + 2 mm)'))
            else:
                assert 'DesignParameters.BillboardBottom' in old, (obj.Name, old)
        for alias, value in [('TextLovelyZ', '=BillboardBottom + 32 mm'),
                             ('TextDrivenZ', '=BillboardBottom + 4 mm'),
                             ('BillboardBottom', '=OverallHeight + 62 mm * 2 / 3')]:
            sheet.set(sheet.getCellFromAlias(alias), value)
        sheet.set('C' + sheet.getCellFromAlias('BillboardBottom')[1:],
                  '主体上方露出竖杆原62 mm，保留2/3为41.333 mm，2026-10-26')
        doc.recompute()
        invalid = [(o.Name, list(o.State)) for o in doc.Objects
                   if any(s in o.State for s in ('Invalid', 'Error'))]
        assert not invalid, invalid
        assert abs(sheet.PostHeight.Value - post_length) < 1e-7
        assert abs(sheet.BillboardBottom.Value - sheet.OverallHeight.Value - original_exposed * 2 / 3) < 1e-7
        unchanged = []
        for b in bodies:
            assert b.Shape.isValid() and len(b.Shape.Solids) == 1, b.Name
            if b.Name == 'billboard_Body':
                continue
            expected = original[b.Name].copy()
            if b.Name in moved:
                expected.translate(App.Vector(0, 0, move_z))
            else:
                unchanged.append(b.Name)
            assert difference(expected, global_shape(b)) < 1e-5, b.Name
        old = original['billboard_Body']
        new = global_shape(doc.billboard_Body)
        assert abs(new.Volume - old.Volume - 2 * 24 * 6 * move_z) < 1e-5
        # The entire sign, including its nut pockets and R3 corners, translates
        # rigidly. The post bases, buried contact region and R2 corners stay put.
        old_board = old.common(Part.makeBox(202, 20, 70, App.Vector(-1, 155, before_bottom)))
        old_board.translate(App.Vector(0, 0, move_z))
        new_board = new.common(Part.makeBox(202, 20, 70, App.Vector(-1, 155, target_bottom)))
        assert difference(old_board, new_board) < 1e-5
        buried = Part.makeBox(202, 20, 88, App.Vector(-1, 155, 150))
        assert difference(old.common(buried), new.common(buried)) < 1e-5
        post_graphics = []
        for name in ('M_Paint_Post_1', 'M_Paint_Post_2'):
            obj = doc.getObject(name)
            assert obj.Shape.isValid() and not obj.Shape.isNull(), name
            assert abs(obj.Shape.BoundBox.ZMin - 150) < 1e-6
            assert abs(obj.Shape.BoundBox.ZMax - target_bottom) < 1e-6
            assert len(obj.Shape.Solids) == 0
            post_graphics.append(dict(name=name, color=obj.MColor, height_mm=post_length))
        sketches = [o for o in doc.Objects if o.TypeId == 'Sketcher::SketchObject']
        assert all(s.FullyConstrained for s in sketches)
        for b in bodies:
            assert styles[b.Name] == (tuple(b.ViewObject.ShapeColor), tuple(b.ViewObject.DiffuseColor)), b.Name
        # New placements must not intersect any stationary part of the assembly.
        for name in moved | {'billboard_Body'}:
            shape = global_shape(doc.getObject(name))
            for fixed in unchanged:
                other = original[fixed]
                if shape.BoundBox.intersect(other.BoundBox):
                    assert shape.common(other).Volume < 1e-5, (name, fixed)
        doc.commitTransaction()
    except Exception:
        doc.abortTransaction()
        raise
    Gui.Selection.clearSelection()
    Gui.activeDocument().activeView().fitAll()
    Gui.updateGui()
    doc.save()
    Gui.activeDocument().activeView().saveImage(
        str(ROOT / 'reports/shorter-billboard-posts-preview.png'), 2000, 1350, 'White')
    result = dict(status='passed', date='2026-10-26', formal_cad=str(CAD),
                  backup=str(BACKUP), before_sha256=sha(BACKUP), after_sha256=sha(CAD),
                  correction_backup=str(CORRECTION_BACKUP) if CORRECTION_BACKUP.exists() else None,
                  shortening_reference='Exposed post length above the 238 mm main body',
                  original_exposed_post_length_mm=original_exposed,
                  new_exposed_post_length_mm=original_exposed * 2 / 3,
                  exposed_length_retained_ratio=2 / 3,
                  old_post_length_mm=150, new_post_length_mm=post_length,
                  reduction_mm=original_exposed / 3,
                  billboard_bottom_mm=target_bottom, total_height_mm=target_bottom + 64,
                  clearance_above_body_mm=original_exposed * 2 / 3, bottom_contact_region_unchanged=True,
                  billboard_and_top_lettering_shape_preserved=True,
                  moved_bodies=sorted(moved), unchanged_bodies=unchanged,
                  all_body_colors_preserved=True, post_color_faces=post_graphics,
                  body_count=len(bodies), fully_constrained_sketches=len(sketches),
                  print_files_regenerated=False)
    REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print('PASS: exposed posts 62 → 41.333 mm (retain 2/3); billboard lowered 20.667 mm from the original.')
    return result
