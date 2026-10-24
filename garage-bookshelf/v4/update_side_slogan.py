"""Replace only the formal CAD's removable side-plate lettering in place.

Run with FreeCAD's bundled Python. Never invoke the historical full builder.
The existing plate, screw hole, corner fillet, placements and other Bodies stay.
"""
import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, '/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as App
import Part
from geometry.sketches import loops
from parameters import evaluate
from assembly import global_shape

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(cad, backup, report):
    cad, backup, report = map(Path, (cad, backup, report))
    if backup.exists():
        raise RuntimeError('Use a new backup path; an existing backup is never overwritten.')
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(cad, backup)
    data = json.loads((ROOT / 'reference/sign-lettering.json').read_text())
    doc = App.openDocument(str(cad))
    body = doc.side_cartridge_Body
    original = {b.Name: b.Shape.copy() for b in doc.Objects if b.TypeId == 'PartDesign::Body'}
    placements = {o.Name: str(o.Placement) for o in doc.Objects if 'Placement' in o.PropertiesList}
    binder = doc.Binder_SignLettering
    old_sketches = [s for s, _ in binder.Support]
    pocket = doc.Pocket_EngravedSlogan
    tip = body.Tip
    assert tip.TypeId == 'PartDesign::Fillet' and old_sketches
    # Match exterior edges geometrically if OpenCascade renumbers them after the edit.
    base, edge_names = tip.Base
    from round_exposed_corners import endpoints
    corners = [endpoints(base.Shape.Edges[int(n[4:]) - 1]) for n in edge_names]
    radius = tip.Radius.Value
    longest = max(row['width_per_cap_height'] for row in data['lines'])
    top = f'(SignHeight+{longest:.12g}*SignTextHeight)/2'
    sketches = []
    rows = []
    for index, row in enumerate(data['lines'], 1):
        print('Building', row['text'], flush=True)
        origin = f'(SignWidth-2*SignTextHeight-SignColumnGap)/2+{index-1}*(SignTextHeight+SignColumnGap)'
        group = []
        for number, indices in enumerate(row['glyphs'], 1):
            polygons = [[(f'{origin}+({y:.12g})*SignTextHeight',
                          f'{top}-({x:.12g})*SignTextHeight')
                         for x, y in row['polygons'][i]] for i in indices]
            s = loops(body, f'Sketch_NewSlogan{index}_{number}', polygons,
                      orientation='XZ', offset=('Zero', f'{evaluate(doc, "CarrierFront")} mm', 'Zero'))
            s.setExpression('Placement.Base.y', 'DesignParameters.CarrierFront')
            s.Label = f'口号 {index}.{number}: {row["text"]}'
            s.addProperty('App::PropertyInteger', 'SignLine', 'Lettering')
            s.SignLine = index
            sketches.append(s)
            group.append(s)
        face = Part.makeCompound([Part.makeFace(s.Shape.Wires, 'Part::FaceMakerBullseye') for s in group])
        bb = face.BoundBox
        assert bb.XMin >= 4 and bb.XMax <= 44 and bb.ZMin > 16 and bb.ZMax < 176
        rows.append(dict(text=row['text'], glyphs=len(group),
                         bounds_mm=[bb.XMin, bb.XMax, bb.ZMin, bb.ZMax]))
    body.Tip = tip
    binder.Support = [(s, []) for s in sketches]
    binder.Label = f'口号轮廓集合（{len(sketches)}个字形草图）'
    body.EngravedSlogan = data['slogan']
    doc.recompute()
    # Keep all downstream features, with the same four R3 corner edges.
    edges = []
    for pair in corners:
        found = [i for i, e in enumerate(base.Shape.Edges, 1) if endpoints(e) == pair]
        assert len(found) == 1, (pair, found)
        edges.append('Edge' + str(found[0]))
    tip.Base = (base, edges)
    for old in old_sketches:
        doc.removeObject(old.Name)
    doc.recompute()
    for s in sketches:
        if s.ViewObject:
            s.ViewObject.Visibility = False
    body.Tip = tip
    area = sum(Part.makeFace(s.Shape.Wires, 'Part::FaceMakerBullseye').Area for s in sketches)
    blank = pocket.BaseFeature.Shape
    depth = evaluate(doc, 'SignEngraveDepth')
    assert abs(blank.Volume - pocket.Shape.Volume - area * depth) < 1e-4
    cuts = Part.makeCompound([Part.makeFace(s.Shape.Wires, 'Part::FaceMakerBullseye').extrude(App.Vector(0, depth, 0)) for s in sketches])
    assert body.Shape.common(cuts).Volume < 1e-5
    assert tip.Radius.Value == radius == 3
    unchanged = []
    for b in [o for o in doc.Objects if o.TypeId == 'PartDesign::Body']:
        assert b.Shape.isValid() and len(b.Shape.Solids) == 1, b.Name
        if b != body:
            assert original[b.Name].cut(b.Shape).Volume + b.Shape.cut(original[b.Name]).Volume < 1e-6, b.Name
            unchanged.append(b.Name)
        assert placements[b.Name] == str(b.Placement)
    all_sketches = [s for s in doc.Objects if s.TypeId == 'Sketcher::SketchObject']
    assert all(s.FullyConstrained for s in all_sketches)
    invalid = [(o.Name, list(o.State)) for o in doc.Objects if any(k in o.State for k in ('Invalid', 'Error'))]
    assert not invalid, invalid
    interference = []
    shape = global_shape(body)
    for name in unchanged:
        fixed = global_shape(doc.getObject(name))
        if shape.BoundBox.intersect(fixed.BoundBox):
            volume = shape.common(fixed).Volume
            assert volume < .01, (name, volume)
            interference.append(dict(body=name, overlap_mm3=volume))
    doc.save()
    App.closeDocument(doc.Name)
    doc = App.openDocument(str(cad))
    assert doc.side_cartridge_Body.EngravedSlogan == data['slogan']
    assert all(b.Shape.isValid() and len(b.Shape.Solids) == 1 for b in doc.Objects if b.TypeId == 'PartDesign::Body')
    assert all(s.FullyConstrained for s in doc.Objects if s.TypeId == 'Sketcher::SketchObject')
    App.closeDocument(doc.Name)
    result = dict(status='passed', slogan=data['slogan'], lines=rows,
                  original_sha256=sha(backup), cad_sha256=sha(cad),
                  body_count=len(original), unchanged_bodies=unchanged,
                  fully_constrained_sketches=len(all_sketches), saved_reopened=True,
                  corner_radius_mm=radius, engraved_depth_mm=depth,
                  remaining_plate_thickness_mm=blank.BoundBox.YLength-depth,
                  engraved_area_mm2=area, interference_checks=interference,
                  print_files_regenerated=False)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print('PASS', report, flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--cad', type=Path, default=ROOT/'garage-bookshelf-v4-assembly.FCStd')
    p.add_argument('--backup', type=Path, required=True)
    p.add_argument('--report', type=Path, default=ROOT/'reports/side-slogan-validation.json')
    args = p.parse_args()
    run(args.cad, args.backup, args.report)
