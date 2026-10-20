"""Create an editable FreeCAD model using Bodies, Sketches, Pads and Pockets.
This is a parametric mechanical reference, not a mesh import. It intentionally
omits decorative text/roundel inlays and approximates some cosmetic details, but
keeps the tested replaceable-interface geometry and the updated front fascia fit.
Run with:
PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib \
/Applications/FreeCAD.app/Contents/Resources/bin/python export_parametric_freecad.py
"""
from pathlib import Path
import json
import FreeCAD as App
import Part, Sketcher  # noqa: F401

HERE = Path(__file__).resolve().parent
OUT = HERE / 'generated' / 'BMW-Modular-V2-DRAFT-parametric.FCStd'
REPORT = HERE / 'generated' / 'BMW-Modular-V2-DRAFT-parametric-report.json'
GAP = 0.30
FRONT_SIGN_GAP = 0.20
FRONT_SIGN_RIB = 0.12

COLORS = {
    'black': (0.086, 0.098, 0.114),
    'yellow': (0.957, 0.835, 0.176),
    'grey': (0.592, 0.612, 0.639),
    'white': (1, 1, 1),
    'blue': (0, 0.4, 0.8),
    'interface': (0.2, 0.75, 0.9),
}
PLATE_OFFSETS = {
    1: App.Vector(0, 0, 0), 2: App.Vector(245, 0, 0), 3: App.Vector(490, 0, 0),
    4: App.Vector(0, -245, 0), 5: App.Vector(245, -245, 0), 6: App.Vector(490, -245, 0),
}
PLATE_NAMES = {
    1: 'Plate 1 Road and parking UNIVERSAL',
    2: 'Plate 2 Showroom UNIVERSAL updated fascia receiver',
    3: 'Plate 3 Glass BMW KIT plain parametric envelope',
    4: 'Plate 4 Signs BMW KIT updated pegs and ribs',
    5: 'Plate 5 Wheel stops UNIVERSAL',
    6: 'Plate 6 Office BMW KIT simplified parametric envelope',
}

doc = App.newDocument('BMW_Modular_V2_DRAFT_parametric')
doc.Comment = ('Parametric FreeCAD reconstruction using PartDesign Body/Sketch/Pad/Pocket. '
               'Generated from modular-v2 dimensions; decorative BMW artwork omitted. '
               'Front fascia updated after fit test: 0.20 mm sockets, peg friction ribs, rear support ledge.')
groups = {}
counts = {'bodies': 0, 'sketches': 0, 'pads': 0, 'pockets': 0}


def safe(s):
    return ''.join(c if c.isalnum() else '_' for c in s).strip('_')[:80]


def group(plate):
    if plate not in groups:
        g = doc.addObject('App::DocumentObjectGroup', safe(PLATE_NAMES[plate]))
        g.Label = PLATE_NAMES[plate]
        groups[plate] = g
    return groups[plate]


def body(name, plate, color='grey'):
    b = doc.addObject('PartDesign::Body', safe(name))
    b.Label = name
    b.Placement.Base = PLATE_OFFSETS[plate]
    group(plate).addObject(b)
    counts['bodies'] += 1
    try:
        b.ViewObject.ShapeColor = COLORS.get(color, COLORS['grey'])
    except Exception:
        pass
    return b


def rect_sketch_xy(b, name, x0, x1, y0, y1, z=0):
    sk = b.newObject('Sketcher::SketchObject', safe(name))
    sk.Placement.Base = App.Vector(0, 0, z)
    pts = [(x0, y0, 0), (x1, y0, 0), (x1, y1, 0), (x0, y1, 0)]
    for a, c in zip(pts, pts[1:] + pts[:1]):
        sk.addGeometry(Part.LineSegment(App.Vector(*a), App.Vector(*c)), False)
    counts['sketches'] += 1
    return sk


def rect_sketch_xz(b, name, x0, x1, z0, z1, y=0):
    sk = b.newObject('Sketcher::SketchObject', safe(name))
    sk.Placement.Base = App.Vector(0, y, 0)
    sk.Placement.Rotation = App.Rotation(App.Vector(1, 0, 0), 90)
    pts = [(x0, z0, 0), (x1, z0, 0), (x1, z1, 0), (x0, z1, 0)]
    for a, c in zip(pts, pts[1:] + pts[:1]):
        sk.addGeometry(Part.LineSegment(App.Vector(*a), App.Vector(*c)), False)
    counts['sketches'] += 1
    return sk


def pad_rect(name, plate, x0, x1, y0, y1, z0, z1, color='grey'):
    b = body(name, plate, color)
    sk = rect_sketch_xy(b, name + ' Sketch', x0, x1, y0, y1, z0)
    p = b.newObject('PartDesign::Pad', safe(name + ' Pad'))
    p.Profile = sk
    p.Length = z1 - z0
    b.Tip = p
    counts['pads'] += 1
    return b


def pocket_xy(b, name, x0, x1, y0, y1, z_top, depth):
    sk = rect_sketch_xy(b, name + ' Sketch', x0, x1, y0, y1, z_top)
    pk = b.newObject('PartDesign::Pocket', safe(name + ' Pocket'))
    pk.Profile = sk
    pk.Length = depth
    b.Tip = pk
    counts['pockets'] += 1
    return pk


def pocket_xz_cut_forward(b, name, x0, x1, z0, z1, y_back, depth):
    # Sketch plane is XZ; pad/pocket direction is -Y with the +90deg X rotation.
    sk = rect_sketch_xz(b, name + ' Sketch', x0, x1, z0, z1, y_back)
    pk = b.newObject('PartDesign::Pocket', safe(name + ' Pocket'))
    pk.Profile = sk
    pk.Length = depth
    b.Tip = pk
    counts['pockets'] += 1
    return pk


def rail_body(name, plate, cx, z, color='interface'):
    half = 1 + GAP
    b = pad_rect(name, plate, cx-half-2, cx+half+2, 20, 101, z, z+3, color)
    pocket_xy(b, name + ' channel clear 0.30 each side', cx-half, cx+half, 19.8, 99.3, z+3, 3.3)
    return b


def peg_blocks(prefix, plate, cx, yfront, zbottom, ribs=False):
    # Approximate transformed sign peg envelope in assembly coordinates.
    objs = []
    objs.append(pad_rect(prefix + ' peg main', plate, cx-4, cx+4, yfront+2.0, yfront+6.0, zbottom+2.4, zbottom+6.4, 'blue'))
    objs.append(pad_rect(prefix + ' peg lead in', plate, cx-3.3, cx+3.3, yfront+2.0, yfront+6.0, zbottom+6.4, zbottom+7.4, 'blue'))
    if ribs:
        objs.append(pad_rect(prefix + ' left friction rib', plate, cx-4-FRONT_SIGN_RIB, cx-4, yfront+2.7, yfront+5.3, zbottom+3.0, zbottom+6.2, 'interface'))
        objs.append(pad_rect(prefix + ' right friction rib', plate, cx+4, cx+4+FRONT_SIGN_RIB, yfront+2.7, yfront+5.3, zbottom+3.0, zbottom+6.2, 'interface'))
    return objs


# Plate 1: floor and interface rails
floor = pad_rect('P1 floor slab with locator pockets', 1, -110, 110, -110, 110, 0, 4, 'black')
for x, y in [(-106, 35), (-106, 94), (106, 35), (106, 94)]:
    pocket_xy(floor, f'locator pocket {x} {y}', x-1.5, x+1.5, y-4.3, y+4.3, 4.05, 2.4)
for cx in [-30, 45]:
    rail_body(f'P1 lower partition rail X{cx}', 1, cx, 4)
# Office rails
for x0, x1 in [(47.5, 49.7), (98.3, 100.5)]:
    pad_rect(f'P1 office side rail {x0}', 1, x0, x1, 25, 94, 4, 8, 'interface')
pad_rect('P1 office left upper lip', 1, 47.5, 51.2, 25, 94, 6.6, 8, 'interface')
pad_rect('P1 office right upper lip', 1, 96.8, 100.5, 25, 94, 6.6, 8, 'interface')
pad_rect('P1 office rear stop', 1, 49.7, 98.3, 91.3, 94, 4, 8, 'interface')

# Plate 2: showroom shell, updated fascia sockets and support ledge
pad_rect('P2 roof slab', 2, -108, 108, 20, 108, 84, 92, 'grey')
pad_rect('P2 left wall', 2, -108, -104, 20, 108, 4, 84, 'grey')
pad_rect('P2 right wall', 2, 104, 108, 20, 108, 4, 84, 'grey')
pad_rect('P2 rear wall', 2, -104, 104, 104, 108, 4, 84, 'grey')
for cx in [-30, 45]:
    rail_body(f'P2 upper partition rail X{cx}', 2, cx, 81)
# updated continuous support ledge/back-stop
pad_rect('P2 front fascia continuous rear support ledge updated', 2, -104, 104, 20, 22, 92, 104, 'interface')
for x in [-92, 92]:
    b = pad_rect(f'P2 front fascia socket tower X{x} updated 0.20', 2, x-7, x+7, 20, 29, 84, 92, 'grey')
    pocket_xz_cut_forward(b, f'front fascia socket 0.20 X{x}', x-4-FRONT_SIGN_GAP, x+4+FRONT_SIGN_GAP, 85.8, 90.2, 25.7, 6.0)
for x in [-16, 16]:
    b = pad_rect(f'P2 interior sign socket tower X{x} 0.30', 2, x-7, x+7, 99.5, 104, 39, 48, 'grey')
    pocket_xz_cut_forward(b, f'interior sign socket 0.30 X{x}', x-4-GAP, x+4+GAP, 40.7, 45.3, 105.2, 6.0)
for x, y in [(-106, 35), (-106, 94), (106, 35), (106, 94)]:
    pad_rect(f'P2 locating tab {x} {y}', 2, x-1.2, x+1.2, y-4, y+4, 2, 4.1, 'grey')

# Plate 3: two plain partitions; decorative inlays omitted
for i, cx in enumerate([-30, 45], 1):
    pad_rect(f'P3 plain partition {i} panel envelope', 3, cx-1, cx+1, 22, 99, 4.35, 83.65, 'white')
    pad_rect(f'P3 partition {i} front grasp tongue', 3, cx-1, cx+1, 18, 30, 6.35, 24.35, 'white')

# Plate 4: signs, front fascia updated with ribs
pad_rect('P4 front fascia panel 200x20', 4, -100, 100, 17.6, 20.0, 84, 104, 'blue')
for cx in [-92, 92]:
    peg_blocks(f'P4 front fascia X{cx} updated', 4, cx, 17.6, 84, ribs=True)
pad_rect('P4 interior sign panel 54x28', 4, -27, 27, 97.1, 99.5, 39, 67, 'blue')
for cx in [-16, 16]:
    peg_blocks(f'P4 interior sign X{cx}', 4, cx, 97.1, 39, ribs=False)

# Plate 5: wheel stops, simplified parametric blocks
for i, x in enumerate([-81.6, -40.8, 0, 40.8, 81.6], 1):
    pad_rect(f'P5 wheel stop {i}', 5, x-12, x+12, -100, -96, 4, 7, 'yellow')

# Plate 6: office cassette simplified but dimensionally bounded
pad_rect('P6 office tray main', 6, 50, 98, 26, 91, 4.3, 6.3, 'blue')
pad_rect('P6 office tray front pull tab', 6, 68, 80, 21, 27, 4.3, 6.3, 'blue')
pad_rect('P6 reception desk base', 6, 53, 95, 68, 85, 6.3, 23, 'blue')
pad_rect('P6 reception desk top', 6, 52, 96, 66, 87, 23, 25, 'blue')
# Stools as circular Sketch + Pad bodies
for i, x in enumerate([61, 87], 1):
    b = body(f'P6 round stool {i}', 6, 'blue')
    sk = b.newObject('Sketcher::SketchObject', f'P6_stool_{i}_circle_sketch')
    sk.Placement.Base = App.Vector(x, 48, 6.3)
    sk.addGeometry(Part.Circle(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 4.5), False)
    counts['sketches'] += 1
    p = b.newObject('PartDesign::Pad', f'P6_stool_{i}_pad')
    p.Profile = sk
    p.Length = 9
    b.Tip = p
    counts['pads'] += 1

# Add an annotation object with the tested decisions.
ann = doc.addObject('App::Annotation', 'Fit_test_update_notes')
ann.LabelText = ['Fit test update:', 'Front fascia sockets: 0.20 mm per side',
                 'Front fascia pegs: shallow side friction ribs',
                 'P2 front receiver: continuous rear support ledge',
                 'P3 partitions and interior sign: kept as tested']
ann.Position = App.Vector(-110, -370, 0)

doc.recompute()
doc.saveAs(str(OUT))
REPORT.write_text(json.dumps({
    'status': 'parametric FreeCAD file generated',
    'file': str(OUT),
    'counts': counts,
    'notes': [
        'Uses PartDesign Bodies with Sketches, Pads and Pockets; no imported STL meshes.',
        'Decorative BMW text/roundel/checker artwork omitted from this parametric reference.',
        'Complex flared rail mouths are simplified as rectangular clearance pockets.',
        'Front fascia update is included: 0.20 mm sockets, friction ribs, support ledge.',
    ]
}, indent=2))
print(OUT)
print(counts)
