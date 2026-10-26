# Frozen v4 source; use v5/tools or the migrated studies.
if __name__ == '__main__':
    raise SystemExit('Historical entry disabled; see v5/README.md and archive/README.md')

"""Apply the 2026-10-24 corner-only trial to the current formal CAD.

Run using FreeCAD's bundled Python, not the historical full builder. Existing
geometry and interfaces remain in place; native Fillets are appended to Bodies.
The first run saves a byte-for-byte backup and refuses to overwrite that backup.
"""
import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, '/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as App


EXPECTED_SOURCE_SHA256 = 'aa6a0f6874f994a0afb18e3b1609fb7981400647562a899e2373f42112b0b0e0'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def endpoints(edge):
    return sorted(tuple(round(v, 6) for v in p.Point) for p in edge.Vertexes)


def bearing_areas(before, after, support):
    """Measure the collar footprint with a thin solid, not a zero-volume touch."""
    import Part
    box = support.BoundBox
    depth = 0.05
    z = before.BoundBox.ZMin
    slab = support.common(Part.makeBox(box.XLength + 0.2, box.YLength + 0.2,
        depth, App.Vector(box.XMin - 0.1, box.YMin - 0.1, z - depth)))
    assert slab.Volume > 10
    slab.translate(App.Vector(0, 0, depth))
    areas = [shape.common(slab).Volume / depth for shape in (before, after)]
    assert min(areas) > 200
    assert abs(areas[0] - areas[1]) < 1e-5
    return areas


def run(cad, backup, report):
    cad, backup, report = map(Path, (cad, backup, report))
    if sha(cad) != EXPECTED_SOURCE_SHA256:
        raise RuntimeError('Source CAD differs from the frozen pre-rounding revision.')
    if backup.exists():
        raise RuntimeError('Backup already exists; use a new backup path.')
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(cad, backup)
    doc = App.openDocument(str(cad))
    assert not any(o.Name.startswith('Fillet_ExposedCorners') for o in doc.Objects)
    original = {b.Name: b.Shape.copy() for b in doc.Objects if b.TypeId == 'PartDesign::Body'}
    # Edge references below apply to the frozen formal CAD, not old exports.
    # Each operation matches endpoint coordinates after preceding operations.
    plan = {
        'module_1': [(3, [1, 11, 8])],
        'module_2': [(3, [8])],
        'module_3': [(3, [46, 14, 52, 51])],
        'garage_deck_1': [(3, [1, 2, 5, 8])],
        'garage_deck_2': [(3, [1, 2, 5, 8])],
        'garage_deck_3': [(3, [1, 2, 5, 8])],
        'billboard': [(3, [3, 4, 28, 29]), (2, [32, 34, 40, 44])],
        'top_carrier': [(3, [1, 2, 5, 8])],
        'side_receiver': [(3, [7, 9, 13, 14])],
        'side_cartridge': [(3, [1, 2, 5, 8])],
    }
    records = []
    for name, steps in plan.items():
        body = doc.getObject(name + '_Body')
        initial = body.Shape.copy()
        specs = [(r, [endpoints(initial.Edges[i - 1]) for i in ids]) for r, ids in steps]
        for radius, wanted in specs:
            base = body.Tip
            ids = []
            for pair in wanted:
                found = [i for i, e in enumerate(base.Shape.Edges, 1) if endpoints(e) == pair]
                assert len(found) == 1, (name, pair, found)
                ids.append('Edge' + str(found[0]))
            feature = body.newObject('PartDesign::Fillet', 'Fillet_ExposedCorners')
            feature.Label = '外露轮廓圆角 R%g mm · 试改' % radius
            feature.Base = (base, ids)
            feature.Radius = radius
            feature.UseAllEdges = False
            feature.Refine = True
            doc.recompute()
            assert feature.Shape.isValid() and len(feature.Shape.Solids) == 1, (name, feature.State)
            assert 'Invalid' not in feature.State
            body.Tip = feature
            if base.ViewObject:
                base.ViewObject.Visibility = False
            if feature.ViewObject:
                feature.ViewObject.Visibility = True
            records.append(dict(body=name, feature=feature.Name, radius_mm=radius, edges=ids))
            print('ROUNDED', name, radius, flush=True)
        assert initial.Volume > body.Shape.Volume
        # Only subtractive rounding: cannot introduce any new interference.
        assert body.Shape.cut(initial).Volume < 1e-6
    modified = {k + '_Body' for k in plan}
    unchanged = []
    for b in [o for o in doc.Objects if o.TypeId == 'PartDesign::Body']:
        assert b.Shape.isValid() and len(b.Shape.Solids) == 1
        if b.Name not in modified:
            a, c = original[b.Name], b.Shape
            assert a.cut(c).Volume + c.cut(a).Volume < 1e-6
            unchanged.append(b.Name)
    print('CHECKED unchanged bodies', flush=True)
    # F interfaces: both sides retain exactly their original geometry in strips
    # spanning the complete tongue/socket lengths, away from outline roundovers.
    import Part
    interfaces = []
    for n, width in [(1, 200), (2, 145), (3, 145)]:
        b = doc.getObject('module_%d_Body' % n)
        for side, x in [('left', -1), ('right', width - 1)]:
            if (n, side) in [(1, 'left'), (3, 'right')]:
                continue  # Exterior ends are not assembly interfaces.
            for y, z, sy, sz in [(23, -1, 35, 11), (109, -1, 35, 11),
                                      (157, 45, 10, 42), (157, 159, 10, 42)]:
                region = Part.makeBox(17, sy, sz, App.Vector(x, y, z))
                old, new = original[b.Name].common(region), b.Shape.common(region)
                error = old.cut(new).Volume + new.cut(old).Volume
                assert error < 1e-6, (b.Name, side, error)
            interfaces.append(dict(body=b.Name, side=side, geometry_unchanged=True))
    print('CHECKED F interfaces', flush=True)
    # Flat contact areas between every layer and its four supporting collars.
    sys.path.insert(0, str(cad.parent))
    from assembly import global_shape
    contacts = []
    for level in (1, 2, 3):
        deck = doc.getObject('garage_deck_%d_Body' % level)
        old = original[deck.Name].copy()
        old.Placement = deck.getGlobalPlacement().multiply(deck.Placement.inverse()).multiply(old.Placement)
        new = global_shape(deck)
        for col in (1, 2, 3, 4):
            support = global_shape(doc.getObject('column_%d_segment_%d_Body' % (col, level)))
            before, after = bearing_areas(old, new, support)
            assert abs(after-before) < 1e-5, (level, col, before, after)
            contacts.append(dict(layer=level, column=col, before_mm2=before, after_mm2=after))
    sketches = [o for o in doc.Objects if o.TypeId == 'Sketcher::SketchObject']
    assert all(s.FullyConstrained for s in sketches)
    doc.recompute()
    doc.save()
    volumes = {b.Name: b.Shape.Volume for b in doc.Objects if b.TypeId == 'PartDesign::Body'}
    App.closeDocument(doc.Name)
    reopened = App.openDocument(str(cad))
    for name, volume in volumes.items():
        b = reopened.getObject(name)
        assert b.Shape.isValid() and len(b.Shape.Solids) == 1
        assert abs(b.Shape.Volume-volume) < 1e-6
    App.closeDocument(reopened.Name)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(dict(status='passed', trial=True, cad=str(cad),
        original_sha256=sha(backup), rounded_sha256=sha(cad), body_count=len(original),
        changed_bodies=sorted(modified), unchanged_bodies=unchanged, fillets=records,
        interface_checks=interfaces, collar_contacts=contacts,
        fully_constrained_sketches=len(sketches), saved_reopened=True,
        scope='Selected exterior corners only; columns, letters, markings, hardware and functional interfaces preserved.',
        print_files_regenerated=False), ensure_ascii=False, indent=2))
    print('PASS', report, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cad', type=Path, default=Path(__file__).parent/'garage-bookshelf-v4-assembly.FCStd')
    parser.add_argument('--backup', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    run(args.cad, args.backup, args.report)
