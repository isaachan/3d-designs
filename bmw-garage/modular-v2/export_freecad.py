"""Parametric FreeCAD export: Body/Sketch/Pad/Pocket, no meshes.

Run in the project venv with FreeCAD on PYTHONPATH, after generate.py:
  PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib \
    ../.venv/bin/python export_freecad.py

Rebuilds every structural interface as PartDesign features in print
orientation (same as the STLs): pads for solids, pockets for sockets and
locator holes, circle pads for stools. Roundel logos are kept as editable
sketch circles; letters and text have no sketch equivalent and are omitted.
Volumes are compared against generate.py's meshes as a regression check.
"""
from pathlib import Path
import json
import sys

import numpy as np
import trimesh as tm
from shapely.geometry import box, Polygon, Point
from shapely.ops import unary_union
import FreeCAD as App
import Part
import Sketcher

try:  # view providers without a full GUI, so colors/visibility persist in the file
    import FreeCADGui as Gui
    Gui.setupWithoutGUI()
    HAS_VIEW = True
except Exception:
    HAS_VIEW = False

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate as g

HERE = Path(__file__).resolve().parent
OUT = HERE / 'generated'
FCSTD = OUT / 'BMW-Modular-V2-DRAFT.FCStd'
V = App.Vector

PLATE_NAMES = {
    1: 'Plate 1 - Road and parking - UNIVERSAL',
    2: 'Plate 2 - Showroom - UNIVERSAL',
    3: 'Plate 3 - Glass - BMW KIT',
    4: 'Plate 4 - Signs - BMW KIT - updated front fascia',
    5: 'Plate 5 - Wheel stops - UNIVERSAL',
    6: 'Plate 6 - Office - BMW KIT',
}

# Filament palette from generate.py: 1 black, 2 yellow, 3 gray, 4 white, 5 blue.
RGB = {1: (0.086, 0.098, 0.114), 2: (0.957, 0.835, 0.176), 3: (0.592, 0.612, 0.639),
       4: (1.0, 1.0, 1.0), 5: (0.0, 0.4, 0.8)}


def style_body(body, filament):
    if not HAS_VIEW or body.ViewObject is None:
        return
    v = body.ViewObject
    v.ShapeColor = RGB[filament]
    v.DisplayMode = 'Shaded'
    v.Transparency = 0
    v.Visibility = True


def hide_sketches(body):
    if not HAS_VIEW:
        return
    for o in body.Group:
        if o.TypeId == 'Sketcher::SketchObject' and o.ViewObject is not None:
            o.ViewObject.Visibility = False


def ring_wires(sketch, poly):
    """Add a shapely polygon (outer ring + holes) to a sketch as line segments."""
    count = 0
    for ring in [poly.exterior, *poly.interiors]:
        pts = list(ring.coords)
        for a, b in zip(pts, pts[1:]):
            sketch.addGeometry(Part.LineSegment(V(a[0], a[1], 0), V(b[0], b[1], 0)), False)
            count += 1
    return count


def add_sketch(doc, container, name, polys, z):
    sk = doc.addObject('Sketcher::SketchObject', name)
    sk.Label = name
    sk.Placement = App.Placement(V(0, 0, z), App.Rotation())
    for poly in polys:
        if poly.is_empty:
            continue
        ring_wires(sk, poly)
    if container is not None:
        container.addObject(sk)
    return sk


def add_feature(doc, body, kind, name, polys, z, length):
    sk = add_sketch(doc, body, f'{name}-sk', polys, z)
    feat = body.newObject(f'PartDesign::{"Pad" if kind == "pad" else "Pocket"}', name)
    feat.Profile = sk
    feat.Length = length
    feat.Midplane = False
    feat.Reversed = False
    doc.recompute()
    return feat


def add_peg(doc, body, name, cx, y0=2.0, length=4.0):
    """Sign peg as built by make_sign after the SIGN axis swap: it stands on the
    panel back (z from 2.4), 8 x 4 section, 5 mm tall with a 1 mm tapered tip.
    Modeled as an exact Y-direction pad of the hexagonal (x, z) profile."""
    sk = doc.addObject('Sketcher::SketchObject', f'{name}-sk')
    sk.Placement = App.Placement(V(0, y0, 0), App.Rotation(V(1, 0, 0), -90))
    hexagon = Polygon([(cx - 4, -2.4), (cx + 4, -2.4), (cx + 4, -6.4),
                       (cx + 3.3, -7.4), (cx - 3.3, -7.4), (cx - 4, -6.4)])
    ring_wires(sk, hexagon)
    body.addObject(sk)
    pad = body.newObject('PartDesign::Pad', name)
    pad.Profile = sk
    pad.Length = length
    doc.recompute()
    return pad


def add_cylinder(doc, body, name, cx, cy, r, z, h):
    sk = doc.addObject('Sketcher::SketchObject', f'{name}-sk')
    sk.Placement = App.Placement(V(0, 0, z), App.Rotation())
    sk.addGeometry(Part.Circle(V(cx, cy, 0), V(0, 0, 1), r), False)
    body.addObject(sk)
    pad = body.newObject('PartDesign::Pad', name)
    pad.Profile = sk
    pad.Length = h
    doc.recompute()
    return pad


def build_body(doc, label, ops, shift, expected=None, tol=1e-4):
    """ops: list of (kind, name, polys, z, length) with z in assembly/print
    design coordinates; shift normalizes the lowest pad to the print bed."""
    body = doc.addObject('PartDesign::Body', label.replace(' ', '_'))
    body.Label = label
    for kind, name, polys, z, length in ops:
        add_feature(doc, body, kind, name, polys, z + shift, length)
    doc.recompute()
    vol = body.Shape.Volume
    report = {'label': label, 'volume_mm3': round(vol, 3), 'features': len(ops)}
    if expected is not None:
        err = abs(vol - expected) / expected
        report['mesh_volume_mm3'] = round(expected, 3)
        report['rel_error'] = round(err, 6)
        assert err < tol, (label, vol, expected, err)
    return body, report


def rail_footprint(cx, mirror_y=False):
    half = 1 + g.GAP
    rect = box(cx - half - 2, 20, cx + half + 2, 101)
    mouth = Polygon([(cx - half - .8, 19), (cx + half + .8, 19), (cx + half, 23),
                     (cx + half, 99.3), (cx - half, 99.3), (cx - half, 23)])
    if mirror_y:
        rect = shapely_mirror(rect)
        mouth = shapely_mirror(mouth)
    return rect.difference(mouth)


def shapely_mirror(poly):
    return _map_polygon(poly, lambda x, y: (x, -y))


def _map_polygon(poly, fn):
    from shapely.geometry import Polygon as P
    ext = [fn(x, y) for x, y in poly.exterior.coords]
    holes = [[fn(x, y) for x, y in ring.coords] for ring in poly.interiors]
    return P(ext, holes)


def rect(x0, x1, y0, y1):
    return box(x0, y0, x1, y1)


def pack_color(rgb):
    r, g, b = (int(round(c * 255)) for c in rgb)
    return str((255 << 24) | (b << 16) | (g << 8) | r)


def patch_gui_document(path, doc, body_filament):
    """Console saves skip GuiDocument.xml (appearance data). Write it directly:
    colored shaded bodies, all sketch/origin lines hidden."""
    import zipfile
    entries = []
    for o in doc.Objects:
        props = []
        if o.TypeId == 'PartDesign::Body':
            filament = body_filament.get(o.Label)
            if filament:
                props.append(('ShapeColor', 'App::PropertyColor',
                              f'<PropertyColor value="{pack_color(RGB[filament])}"/>', True))
            props.append(('Visibility', 'App::PropertyBool',
                          '<Bool value="true"/>', True))
        else:
            props.append(('Visibility', 'App::PropertyBool',
                          '<Bool value="false"/>', False))
        xml = f'<ViewProviderData name="{o.Name}"><Properties Count="{len(props)}">'
        for name, typ, payload, visible in props:
            xml += f'<Property name="{name}" type="{typ}">{payload}</Property>'
        xml += '</Properties></ViewProviderData>'
        entries.append(xml)
    gui = ('<?xml version="1.0" encoding="utf-8"?>\n'
           '<Document SchemaVersion="4" ProgramVersion="FreeCAD 1.1.3" FileVersion="1">'
           + ''.join(entries) + '</Document>')
    with zipfile.ZipFile(path) as zin:
        contents = {n: zin.read(n) for n in zin.namelist()}
    contents['GuiDocument.xml'] = gui.encode()
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zout:
        for n, data in contents.items():
            zout.writestr(n, data)


def main():
    g.build()
    doc = App.newDocument('BMW_Modular_V2_DRAFT')
    doc.Comment = ('Parametric reference rebuilt from generate.py dimensions. '
                   'Structural interfaces are Sketch/Pad/Pocket features in print '
                   'orientation. Roundels are editable circle sketches; BMW '
                   'lettering/text has no sketch equivalent and is omitted.')
    groups = {p: doc.addObject('App::DocumentObjectGroup', PLATE_NAMES[p].replace(' ', '_'))
              for p in PLATE_NAMES}
    reports = []
    mesh_vol = {i: tm.boolean.union(list(it['parts'].values()), engine='manifold').volume
                for i, it in enumerate(g.items)}

    # ---- Plate 1: floor, partition rails, office tray rails, locator pockets.
    ops = [('pad', 'floor', [rect(-110, 110, -110, 110)], 0, 4)]
    for cx in (-30, 45):
        ops.append(('pad', f'partition-rail-{cx:+.0f}', [rail_footprint(cx)], 4, 3))
    for x0, x1 in [(47.5, 49.7), (98.3, 100.5)]:
        ops.append(('pad', f'tray-side-rail-{x0:.1f}', [rect(x0, x1, 25, 94)], 4, 4))
    for x0, x1 in [(47.5, 51.2), (96.8, 100.5)]:
        ops.append(('pad', f'tray-top-guide-{x0:.1f}', [rect(x0, x1, 25, 94)], 6.6, 1.4))
    ops.append(('pad', 'tray-rear-stop', [rect(49.7, 98.3, 91.3, 94)], 4, 4))
    for x, y in [(-106, 35), (-106, 94), (106, 35), (106, 94)]:
        ops.append(('pocket', f'locator-pocket-{x:+.0f}-{y:+.0f}',
                    [rect(x - 1.5, x + 1.5, y - 4.3, y + 4.3)], 4, 2.4))
    body, rep = build_body(doc, 'Plate1 Road floor + rails', ops, 0, mesh_vol[0])
    groups[1].addObject(body)
    reports.append(rep)

    # Road markings: flush 0.4 mm artwork kept as its own pad body (color regions).
    markings = [rect(-102, -105, 102, -103.6), rect(-102, -32, 102, -30.6), rect(-104, 15, 104, 16.4)]
    for x in np.linspace(-102, 102, 6):
        markings.append(rect(x, -105, x + 1.4, -30.6))
    for x in range(-98, 104, 22):
        markings.append(rect(x, -9, x + 12, -7.6))
    for ix in range(15):
        for iy in range(8):
            if (ix + iy) % 2 == 0:
                markings.append(rect(-104 + 10 * ix, 22 + 10 * iy, -94 + 10 * ix, 32 + 10 * iy))
    white = unary_union([m.buffer(-.02, join_style=2) for m in markings])
    for cx in (-30, 45):
        b = rail_footprint(cx).bounds
        white = white.difference(box(b[0] - .2, b[1] - .2, b[2] + .2, b[3] + .2))
    for x0, x1, y0, y1 in [(47.5, 100.5, 25, 94)]:
        white = white.difference(box(x0 - .2, y0 - .2, x1 + .2, y1 + .2))
    polys = list(getattr(white, 'geoms', [white]))
    art = doc.addObject('PartDesign::Body', 'Plate1_white_markings_artwork')
    add_feature(doc, art, 'pad', 'markings', polys, 3.6, 0.4)
    doc.recompute()
    groups[1].addObject(art)

    # ---- Plate 2: shell printed roof-down. y mirrors, z' = 92 - z, then +12.
    S = 12.0  # shift so the new fascia back-stop strip starts at the bed

    def z2(z_asm, h):
        return 92 - z_asm - h + S, h  # base of the pad in print coordinates

    ops = []
    for name, r, z_asm, h in [
        ('fascia-back-stop-strip', rect(-104, 104, 20, 22), 92, 12),
        ('roof-slab', rect(-108, 108, 20, 108), 84, 8),
        ('wall-left', rect(-108, -104, 20, 108), 4, 80),
        ('wall-right', rect(104, 108, 20, 108), 4, 80),
        ('wall-rear', rect(-104, 104, 104, 108), 4, 80),
        ('socket-tower-left', rect(-99, -85, 20, 29), 84, 8),
        ('socket-tower-right', rect(85, 99, 20, 29), 84, 8),
        ('interior-sign-boss-left', rect(-23, -9, 99.5, 104), 39, 9),
        ('interior-sign-boss-right', rect(9, 23, 99.5, 104), 39, 9),
    ]:
        base, height = z2(z_asm, h)
        ops.append(('pad', name, [shapely_mirror(r)], base, height))
    for x, y in [(-106, 35), (-106, 94), (106, 35), (106, 94)]:
        base, height = z2(2, 2.1)
        ops.append(('pad', f'shell-locator-tab-{x:+.0f}-{y:+.0f}',
                    [shapely_mirror(rect(x - 1.2, x + 1.2, y - 4, y + 4))], base, height))
    for cx in (-30, 45):
        base, height = z2(81, 3)
        ops.append(('pad', f'partition-top-rail-{cx:+.0f}',
                    [rail_footprint(cx, mirror_y=True)], base, height))
    for name, r, z_asm, h in [
        ('fascia-socket-left', rect(-92 - 4 - g.FRONT_SIGN_GAP, -92 + 4 + g.FRONT_SIGN_GAP, 19.9, 25.7), 85.8, 4.4),
        ('fascia-socket-right', rect(92 - 4 - g.FRONT_SIGN_GAP, 92 + 4 + g.FRONT_SIGN_GAP, 19.9, 25.7), 85.8, 4.4),
        ('interior-socket-left', rect(-16 - 4 - g.GAP, -16 + 4 + g.GAP, 99.4, 105.2), 40.7, 4.6),
        ('interior-socket-right', rect(16 - 4 - g.GAP, 16 + 4 + g.GAP, 99.4, 105.2), 40.7, 4.6),
        ('rear-cable-notch', rect(88, 96, 103.9, 108.1), 78, 6.2),
    ]:
        base, height = z2(z_asm, h)
        ops.append(('pocket', name, [shapely_mirror(r)], base + height, height))
    body, rep = build_body(doc, 'Plate2 showroom shell', ops, 0, mesh_vol[1])
    groups[2].addObject(body)
    reports.append(rep)

    # ---- Plate 3: two partitions, plain face on the bed.
    for i, cx in enumerate((-30, 45)):
        ops = [('pad', 'panel', [rect(0, 77, 0, 79.3)], 0, 2),
               ('pad', 'grasp-tongue', [rect(-4, 8, 2, 20)], 0, 2)]
        # The reference STL union of tongue and panel carries a known ~48 mm3
        # coplanar-boolean artifact (0.39%), so this body gets a looser check.
        body, rep = build_body(doc, f'Plate3 partition {i + 1}', ops, 0, mesh_vol[2 + i],
                               tol=5e-3)
        groups[3].addObject(body)
        reports.append(rep)
        grp = doc.addObject('App::DocumentObjectGroup', f'Plate3_partition{i + 1}_roundel_artwork')
        for frac in (1.0, .94, .64):
            add_sketch(doc, grp, f'partition{i + 1}-roundel-r{frac:.2f}',
                       [Point(39, 42).buffer(23 * frac, quad_segs=64)], 1.6)
        groups[3].addObject(grp)

    # ---- Plate 4: signs face-down; pegs and friction ribs grow upward.
    def sign_ops(w, h, spacing, ribs):
        ops = [('pad', 'face-panel', [rect(-w / 2, w / 2, 0, h)], 0, 2.4)]
        for x in (-spacing / 2, spacing / 2):
            if ribs:
                for side in (-1, 1):
                    x0 = x + side * 4 - (g.FRONT_SIGN_RIB if side < 0 else 0)
                    x1 = x + side * 4 + (0 if side < 0 else g.FRONT_SIGN_RIB)
                    ops.append(('pad', f'rib-{x:+.0f}-{side}',
                                [rect(x0, x1, 2.7, 5.3)], 3.0, 3.2))
        return ops, [x for x in (-spacing / 2, spacing / 2)]

    fascia_idx = next(i for i, it in enumerate(g.items) if 'fascia' in it['name'])
    inner_idx = next(i for i, it in enumerate(g.items) if 'interior sign' in it['name'])
    body, rep = build_body(doc, 'Plate4 front fascia (0.20 sockets + ribs)',
                           sign_ops(200, 20, 184, True)[0], 0)
    for x in sign_ops(200, 20, 184, True)[1]:
        add_peg(doc, body, f'peg-{x:+.0f}', x)
    doc.recompute()
    vol = body.Shape.Volume
    err = abs(vol - mesh_vol[fascia_idx]) / mesh_vol[fascia_idx]
    rep.update(volume_mm3=round(vol, 3), mesh_volume_mm3=round(mesh_vol[fascia_idx], 3),
               rel_error=round(err, 6))
    assert err < 1e-4, (vol, mesh_vol[fascia_idx], err)
    groups[4].addObject(body)
    reports.append(rep)
    grp = doc.addObject('App::DocumentObjectGroup', 'Plate4_fascia_roundel_artwork')
    r = min(20 * .40, 8)
    for frac in (1.0, .94, .64):
        add_sketch(doc, grp, f'fascia-roundel-r{frac:.2f}',
                   [Point(200 / 2 - r - 3, 10).buffer(r * frac, quad_segs=64)], 0)
    groups[4].addObject(grp)

    ops, peg_xs = sign_ops(54, 28, 32, False)
    body, rep = build_body(doc, 'Plate4 interior sign', ops, 0)
    for x in peg_xs:
        add_peg(doc, body, f'peg-{x:+.0f}', x)
    doc.recompute()
    vol = body.Shape.Volume
    err = abs(vol - mesh_vol[inner_idx]) / mesh_vol[inner_idx]
    rep.update(volume_mm3=round(vol, 3), mesh_volume_mm3=round(mesh_vol[inner_idx], 3),
               rel_error=round(err, 6))
    assert err < 1e-4, (vol, mesh_vol[inner_idx], err)
    groups[4].addObject(body)
    reports.append(rep)
    grp = doc.addObject('App::DocumentObjectGroup', 'Plate4_interior_roundel_artwork')
    r = min(28 * .40, 8)
    for frac in (1.0, .94, .64):
        add_sketch(doc, grp, f'interior-roundel-r{frac:.2f}',
                   [Point(54 / 2 - r - 3, 14).buffer(r * frac, quad_segs=64)], 0)
    groups[4].addObject(grp)

    # ---- Plate 5: wheel stops with flush stripe pads.
    stop_items = [(i, it) for i, it in enumerate(g.items) if it['plate'] == 5]
    for i, (idx, it) in enumerate(stop_items):
        x = [-81.6, -40.8, 0, 40.8, 81.6][i]
        ops = [('pad', 'stop', [rect(x - 12, x + 12, -100, -96)], 4, 3)]
        for a in (-8, -2, 4):
            ops.append(('pad', f'stripe-{a}', [rect(x + a, x + a + 2, -100, -96)], 6.6, .4))
        body, rep = build_body(doc, f'Plate5 wheel stop {i + 1}', ops, -4, mesh_vol[idx])
        groups[5].addObject(body)
        reports.append(rep)

    # ---- Plate 6: office cassette; stools are circle pads.
    ops = [('pad', 'tray', [rect(50, 98, 26, 91)], 4.3, 2),
           ('pad', 'tray-grasp-tongue', [rect(68, 80, 21, 27)], 4.3, 2),
           ('pad', 'desk-body', [rect(53, 95, 68, 85)], 6.3, 16.7),
           ('pad', 'desk-top', [rect(52, 96, 66, 87)], 23, 2)]
    office_idx = next(i for i, it in enumerate(g.items) if it['plate'] == 6)
    body = doc.addObject('PartDesign::Body', 'Plate6_office_cassette')
    body.Label = 'Plate6 office cassette'
    for kind, name, polys, z, length in ops:
        add_feature(doc, body, kind, name, polys, z - 4.3, length)
    for x in (61, 87):
        add_cylinder(doc, body, f'stool-{x}', x, 48, 4.5, 6.3 - 4.3, 9)
    doc.recompute()
    vol = body.Shape.Volume
    err = abs(vol - mesh_vol[office_idx]) / mesh_vol[office_idx]
    reports.append({'label': 'Plate6 office cassette', 'volume_mm3': round(vol, 3),
                    'mesh_volume_mm3': round(mesh_vol[office_idx], 3), 'rel_error': round(err, 6)})
    assert err < 5e-3, (vol, mesh_vol[office_idx])
    groups[6].addObject(body)
    grp = doc.addObject('App::DocumentObjectGroup', 'Plate6_desk_roundel_artwork')
    for frac in (1.0, .94, .64):
        add_sketch(doc, grp, f'desk-roundel-r{frac:.2f}',
                   [Point(74, 76).buffer(7 * frac, quad_segs=64)], 24.6 - 4.3)
    groups[6].addObject(grp)

    # Apply appearance centrally: hide construction geometry, color each body
    # with its dominant filament color from the 3MF palette.
    body_filament = {
        'Plate1 Road floor + rails': 1,
        'Plate1_white_markings_artwork': 4,
        'Plate2 showroom shell': 3,
        'Plate3 partition 1': 4, 'Plate3 partition 2': 4,
        'Plate4 front fascia (0.20 sockets + ribs)': 5,
        'Plate4 interior sign': 5,
        'Plate5 wheel stop 1': 2, 'Plate5 wheel stop 2': 2, 'Plate5 wheel stop 3': 2,
        'Plate5 wheel stop 4': 2, 'Plate5 wheel stop 5': 2,
        'Plate6 office cassette': 5,
    }
    if HAS_VIEW:
        for o in doc.Objects:
            v = o.ViewObject
            if v is None:
                continue
            if o.TypeId in ('Sketcher::SketchObject', 'App::Line', 'App::Plane', 'App::Point'):
                v.Visibility = False
        for o in doc.Objects:
            if o.TypeId == 'PartDesign::Body' and o.Label in body_filament:
                style_body(o, body_filament[o.Label])

    doc.recompute()
    doc.saveAs(str(FCSTD))
    # A real GUI save writes GuiDocument.xml itself; only patch console saves.
    import zipfile
    with zipfile.ZipFile(FCSTD) as z:
        if 'GuiDocument.xml' not in z.namelist():
            patch_gui_document(FCSTD, doc, body_filament)
    try:  # quit when launched as a GUI app so batch runs terminate
        import FreeCADGui as Gui
        Gui.getMainWindow().close()
    except Exception:
        pass
    (OUT / 'freecad-parametric-validation.json').write_text(json.dumps({
        'file': str(FCSTD), 'bodies_checked_against_meshes': reports,
        'notes': ['print orientation, same normalization as the STLs',
                  'roundels are editable circle sketches; letters/text omitted',
                  'colors not set: file written from console Python without GUI'],
    }, indent=2))
    print(FCSTD)
    for rep in reports:
        print(f"{rep['label']}: vol={rep['volume_mm3']} err={rep.get('rel_error')}")


if __name__ == '__main__':
    main()
