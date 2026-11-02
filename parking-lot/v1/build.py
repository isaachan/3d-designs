#!/usr/bin/env python3
"""First native BRep CAD of the approved Parking Lot concept, in millimetres.

Run with the FreeCAD bundled Python. No meshes are converted into CAD solids.
Roads use editable constrained section sketches and native smooth Part::Lofts.
Original column BReps and support geometry are read from the approved concept.
"""
import hashlib
import json
import math
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
CONCEPT = ROOT.parent/'concepts/01-side-helix/geometry-rebuild'
sys.path.insert(0, '/Applications/FreeCAD.app/Contents/Resources/lib')
sys.path.insert(0, str(CONCEPT/'installation'))
sys.path.insert(0, str(CONCEPT/'installation/column-reuse'))
import FreeCAD as App
import Part
import Sketcher
import column_parts as mounts

P = json.loads((ROOT/'parameters.json').read_text())
V = App.Vector
TAU = math.tau
CX, CY = P['road_center']
RI, RO = P['road_inner_radius'], P['road_outer_radius']
W = RO-RI
THICK = P['deck_thickness']
PITCH = P['floor_pitch']
LANDING = math.radians(P['landing_half_angle_deg'])
ALPHA = math.asin(W/2/RO)
BLACK = (.095, .11, .13)
CYAN, BLUE, RED = (.15, .65, .84), (.11, .15, .40), (.89, .13, .17)
WHITE = (.93, .95, .96)
PALETTE = [CYAN, BLUE, RED]
FONT = '/System/Library/Fonts/Supplemental/Arial.ttf'
FINAL = []
MANIFEST = []
GROUPS = {}
DOC = None


def log(msg):
    print(msg, flush=True)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def height(theta):
    q = (theta-math.pi)/TAU
    if q <= 0:
        return P['floor_z'][0]
    if q >= 3:
        return P['floor_z'][3]
    k = math.floor(q)
    run = TAU-2*LANDING
    e = math.radians(P['transition_angle_deg'])
    t = (q-k)*TAU-LANDING
    if t <= 0:
        fraction = 0.
    elif t >= run:
        fraction = 1.
    elif t < e:
        fraction = (t/2-e*math.sin(math.pi*t/e)/(2*math.pi))/(run-e)
    elif t <= run-e:
        fraction = (t-e/2)/(run-e)
    else:
        v = run-t
        fraction = (run-e-(v/2-e*math.sin(math.pi*v/e)/(2*math.pi)))/(run-e)
    return P['floor_z'][0]+PITCH*(k+fraction)


def point(r, a, z):
    return V(CX+r*math.cos(a), CY+r*math.sin(a), z)


def group(name, label):
    if name not in GROUPS:
        obj = DOC.addObject('App::DocumentObjectGroup', name)
        obj.Label = label
        GROUPS[name] = obj
    return GROUPS[name]


def metadata(obj, category, color=BLACK, final=True, source='New CAD v1'):
    for typ, prop, value in [('App::PropertyString', 'DesignRole', category),
                             ('App::PropertyColor', 'DesignColor', color),
                             ('App::PropertyBool', 'DeliveryVisible', final),
                             ('App::PropertyString', 'GeometrySource', source)]:
        obj.addProperty(typ, prop, 'Parking Lot')
        setattr(obj, prop, value)
    if final:
        FINAL.append(obj)
    return obj


def feature(name, shape, category, color=BLACK, parent=None, final=True, source='New CAD v1'):
    assert shape.isValid(), name
    assert shape.Solids and all(s.isClosed() and s.Volume > 1e-8 for s in shape.Solids), name
    obj = DOC.addObject('Part::Feature', name)
    obj.Shape = shape
    metadata(obj, category, color, final, source)
    if parent is not None:
        parent.addObject(obj)
    return obj


def compound(shapes):
    return Part.makeCompound(shapes)


def rect_sketch(name, x0, y0, dx, dy, placement, parent, expressions=None):
    sk = DOC.addObject('Sketcher::SketchObject', name)
    sk.Placement = placement
    pts = [V(x0, y0, 0), V(x0+dx, y0, 0), V(x0+dx, y0+dy, 0), V(x0, y0+dy, 0)]
    sk.addGeometry([Part.LineSegment(pts[i], pts[(i+1)%4]) for i in range(4)], False)
    for i in range(4):
        sk.addConstraint(Sketcher.Constraint('Coincident', i, 2, (i+1)%4, 1))
        sk.addConstraint(Sketcher.Constraint('Horizontal' if i%2 == 0 else 'Vertical', i))
    for constraint in [('DistanceX', 0, 1, x0), ('DistanceY', 0, 1, y0),
                       ('Distance', 0, dx), ('Distance', 1, dy)]:
        sk.addConstraint(Sketcher.Constraint(*constraint))
    # Constraints 8..11 describe location, width and height. Zero-distance
    # constraints are accepted by Sketcher and reported fully constrained.
    for index, expr in (expressions or {}).items():
        sk.setExpression(f'Constraints[{index}]', expr)
    parent.addObject(sk)
    return sk


def sheet():
    s = DOC.addObject('Spreadsheet::Sheet', 'DesignParameters')
    s.Label = '尺寸参数（完整更新请运行 build.py）'
    s.set('A1', 'Parking Lot CAD v1 · mm')
    rows = [('GarageWidth', P['garage_width']), ('GarageDepth', P['garage_depth']),
            ('FloorPitch', PITCH), ('FirstFloorZ', P['floor_z'][0]),
            ('RoadInnerRadius', RI), ('LaneWidth', W), ('DeckThickness', THICK),
            ('CurbThickness', P['curb_thickness']), ('CurbHeight', P['curb_height'])]
    for row, (alias, value) in enumerate(rows, 3):
        s.set(f'A{row}', alias)
        s.set(f'B{row}', str(value))
        s.setAlias(f'B{row}', alias)
    s.setColumnWidth('A', 250)
    s.setColumnWidth('B', 120)
    s.set('A14', 'Source of truth: parameters.json + build.py')
    s.set('A15', 'Loft profiles/deck pads have native expressions.')
    s.set('A16', 'Supports, holes, landings: rebuild for assembly-wide changes.')
    return s


def annulus(r0, r1, a, b, z, thickness):
    mid = (a+b)/2
    outer = Part.Arc(point(r1, a, z), point(r1, mid, z), point(r1, b, z)).toShape()
    inner = Part.Arc(point(r0, b, z), point(r0, mid, z), point(r0, a, z)).toShape()
    wire = Part.Wire([outer, Part.makeLine(point(r1, b, z), point(r0, b, z)),
                      inner, Part.makeLine(point(r0, a, z), point(r1, a, z))])
    return Part.Face(wire).extrude(V(0, 0, thickness))


def bridge(z):
    lo, hi = point(RO, math.pi+ALPHA, z), point(RO, math.pi-ALPHA, z)
    leftlo, lefthi = V(P['garage_width'], CY-W/2, z), V(P['garage_width'], CY+W/2, z)
    wire = Part.Wire([Part.makeLine(leftlo, lo),
                      Part.Arc(lo, point(RO, math.pi, z), hi).toShape(),
                      Part.makeLine(hi, lefthi), Part.makeLine(lefthi, leftlo)])
    return Part.Face(wire).extrude(V(0, 0, -THICK))


def polygon_solid(points, dz):
    vs = [V(*p) for p in points]
    return Part.Face(Part.makePolygon(vs+[vs[0]])).extrude(V(0, 0, dz))


def smooth_loft(name, a, b, r0, r1, low, high, color, category, use_sketches=False):
    count = round(math.degrees(b-a)/P['loft_section_step_deg'])
    profiles = []
    parent = group('Construction', '90 · 道路放样截面（隐藏）')
    for i in range(count+1):
        theta = a+(b-a)*i/count
        z = height(theta)
        if use_sketches:
            rot = App.Rotation(V(0, 0, 1), math.degrees(theta)).multiply(App.Rotation(V(1, 0, 0), 90))
            sk = rect_sketch(f'{name}_Section_{i:03}', r0, low, r1-r0, high-low,
                             App.Placement(V(CX, CY, z), rot), parent,
                             {8: 'DesignParameters.RoadInnerRadius',
                              9: '-DesignParameters.DeckThickness',
                              10: 'DesignParameters.LaneWidth',
                              11: 'DesignParameters.DeckThickness'})
        else:
            vs = [point(r0, theta, z+low), point(r1, theta, z+low),
                  point(r1, theta, z+high), point(r0, theta, z+high)]
            sk = DOC.addObject('Part::Feature', f'{name}_Section_{i:03}')
            sk.Shape = Part.makePolygon(vs+[vs[0]])
            parent.addObject(sk)
        profiles.append(sk)
    obj = DOC.addObject('Part::Loft', name)
    obj.Sections = profiles
    obj.Solid = True
    obj.Ruled = False
    obj.Closed = False
    metadata(obj, category, color, final=not use_sketches)
    group('Road' if use_sketches else 'Curbs', '02 · 连续主道路' if use_sketches else '03 · 三色护栏').addObject(obj)
    return obj


def build_road():
    roads = []
    road_group = group('Road', '02 · 连续主道路')
    curb_group = group('Curbs', '03 · 三色护栏')
    for k in range(3):
        a, b = math.pi+k*TAU+LANDING, math.pi+(k+1)*TAU-LANDING
        roads.append(smooth_loft(f'RisingRoad_{k+1}', a, b, RI, RO, -THICK, 0, BLACK, 'road-source', True))
        smooth_loft(f'InnerCurb_Rise_{k+1}', a, b, RI-2, RI, 0, 8, PALETTE[k], 'curb')
        smooth_loft(f'OuterCurb_Rise_{k+1}', a, b, RO, RO+2, 0, 8, PALETTE[k], 'curb')
    clip = mounts.box(-50, 700, CY-W/2, 350, -30, 400)
    for k, z in enumerate(P['floor_z']):
        mid = math.pi+k*TAU
        landing = annulus(RI, RO, mid-LANDING, mid+LANDING, z-THICK, THICK)
        if k == 3:
            landing = landing.common(clip).removeSplitter()
        roads.append(feature(f'Landing_{k+1}F', landing, 'road-source', parent=road_group, final=False))
        roads.append(feature(f'Bridge_{k+1}F', bridge(z), 'road-source', parent=road_group, final=False))
        for j, (a, b) in enumerate([(mid-LANDING, mid), (mid, mid+LANDING)]):
            color = PALETTE[min(2, max(0, k-1 if j == 0 else k))]
            sh = annulus(RI-2, RI, a, b, z, 8)
            if k == 3:
                sh = sh.common(clip).removeSplitter()
            feature(f'InnerCurb_Landing_{k+1}_{j}', sh, 'curb', color, curb_group)
        for j, (a, b) in enumerate([(mid-LANDING, mid-ALPHA), (mid+ALPHA, mid+LANDING)]):
            if k == 3 and j == 1:
                continue
            color = PALETTE[min(2, max(0, k-1 if j == 0 else k))]
            feature(f'OuterCurb_Landing_{k+1}_{j}', annulus(RO, RO+2, a, b, z, 8), 'curb', color, curb_group)
        for side in (-1, 1):
            if k == 3 and side == -1:
                continue
            y0, y1 = sorted([CY+side*W/2, CY+side*(W/2+2)])
            x0 = CX-math.sqrt(RO**2-(y0-CY)**2)
            x1 = CX-math.sqrt(RO**2-(y1-CY)**2)
            # Exact circular end, with the same outside boundary as the road.
            p0, pm, p1 = V(x0, y0, z), V(CX-math.sqrt(RO**2-((y0+y1)/2-CY)**2), (y0+y1)/2, z), V(x1, y1, z)
            edges = [Part.makeLine(V(200, y0, z), p0), Part.Arc(p0, pm, p1).toShape(),
                     Part.makeLine(p1, V(200, y1, z)), Part.makeLine(V(200, y1, z), V(200, y0, z))]
            feature(f'BridgeCurb_{k+1}_{side+1}', Part.Face(Part.Wire(edges)).extrude(V(0, 0, 8)),
                    'curb', PALETTE[min(2, max(0, k-1))], curb_group)
    # Stop outside the 1F side opening; terminate 4F at its bridge's front edge.
    t = math.pi-LANDING
    p = [point(r, a, P['floor_z'][0]) for r, a in [(RI-2, t-1/120), (RO+2, t-1/120),
                                                  (RO+2, t+1/120), (RI-2, t+1/120)]]
    feature('Curb_1F_EndStop', polygon_solid([tuple(v) for v in p], 8), 'curb', CYAN, curb_group)
    xi = CX-math.sqrt((RI-2)**2-(W/2)**2)
    feature('Curb_4F_FlushEnd', mounts.box(200, xi, CY-W/2-2, CY-W/2, 197, 205), 'curb', RED, curb_group)
    DOC.recompute()
    union = DOC.addObject('Part::MultiFuse', 'ContinuousRoad_BeforeHoles')
    union.Shapes = roads
    union.Refine = True
    road_group.addObject(union)
    metadata(union, 'road-source', final=False)
    DOC.recompute()
    assert union.Shape.isValid() and len(union.Shape.Solids) == 1, 'Road must be one connected solid'
    return union


def pad_deck(k, parent):
    z = P['floor_z'][k]
    body = DOC.addObject('PartDesign::Body', f'Deck_{k+1}F')
    parent.addObject(body)
    sk = rect_sketch(f'Deck_{k+1}F_Outline', 0., 0., 200., 230.,
                     App.Placement(V(0, 0, z-THICK), App.Rotation()), body,
                     {10: 'DesignParameters.GarageWidth', 11: 'DesignParameters.GarageDepth'})
    sk.setExpression('Placement.Base.z', f'DesignParameters.FirstFloorZ+{k}*DesignParameters.FloorPitch-DesignParameters.DeckThickness')
    pad = body.newObject('PartDesign::Pad', f'Deck_{k+1}F_Pad')
    pad.Profile = sk
    pad.setExpression('Length', 'DesignParameters.DeckThickness')
    hs = body.newObject('Sketcher::SketchObject', f'Deck_{k+1}F_LocatingHoles')
    hs.Placement.Base = V(0, 0, z)
    hs.setExpression('Placement.Base.z', f'DesignParameters.FirstFloorZ+{k}*DesignParameters.FloorPitch')
    for x in (12, 188):
        for y in (14, 216):
            index = hs.addGeometry(Part.Circle(V(x, y, 0), V(0, 0, 1), 3.25), False)
            hs.addConstraint(Sketcher.Constraint('Block', index))
    hole = body.newObject('PartDesign::Pocket', f'Deck_{k+1}F_PinHoles')
    hole.Profile = hs
    hole.setExpression('Length', 'DesignParameters.DeckThickness')
    body.Tip = hole
    metadata(body, 'garage-deck', BLACK)
    DOC.recompute()
    return body


def build_garage():
    parent = group('Garage', '01 · 停车楼与底座')
    # The concept's ground platform intersects its thin base. They become one
    # foundation solid in CAD, rather than two physically overlapping parts.
    x0, x1, y0, y1 = P['base_bounds']
    base = mounts.box(x0, x1, y0, y1, 0, P['base_thickness'])
    locations = []
    for i, degree in enumerate(P['support_angles_deg']):
        t = math.radians(degree)
        locations.append((f'B{i+1}', t, CX+169*math.cos(t), CY+169*math.sin(t)))
    locations.append(('C', 0., 602., 74.))
    for name, t, x, y in locations:
        base = base.fuse(mounts.transformed(mounts.base_pad(), t, (x, y, 0)))
        for v in (-10.5, 10.5):
            base = base.cut(Part.makeCylinder(1.7, 5, V(x-v*math.sin(t), y+v*math.cos(t), -3)))
    base = base.fuse(mounts.box(0, 200, 0, 230, 1.3, 8))
    for x in (12, 188):
        for y in (14, 216):
            base = base.fuse(Part.makeCylinder(3, 3, V(x, y, 8)))
    feature('Foundation_And_1F', base.removeSplitter(), 'foundation', BLACK, parent)
    for i, (x, y) in enumerate([(3, -77), (3, 227), (612, -77), (612, 227)]):
        feature(f'FootPad_{i+1}', Part.makeCylinder(8, 6, V(x, y, -6)), 'foot-pad', BLACK, parent)
    for k in range(1, 4):
        pad_deck(k, parent)
    # Rear wall is outside the full 200 x 230 deck plan, avoiding a 1-mm
    # intersection present in the illustrative concept. Its feet join base.
    feature('Garage_BackWall', mounts.box(0, 200, 230, 234, 1.3, 232), 'back-wall', BLACK, parent)
    columns = group('GarageColumns', '04 · 原车库四柱')
    for i, (x, y) in enumerate([(12, 14), (12, 216), (188, 14), (188, 216)]):
        for k, z in enumerate(P['floor_z']):
            sh = mounts.garage_segment(z, k == 3)
            sh.translate(V(x, y, 0))
            feature(f'A{i+1}_Column_{k+1}', sh, 'original-column', BLACK, columns,
                    source='garage-bookshelf v5 BRep snapshot: top-cap' if k == 3 else 'garage-bookshelf v5 BRep snapshot: standard')
    return locations


def build_supports(locations, roadway):
    parent = group('RampSupports', '05 · 坡道分段柱与托臂')
    hardware = group('Hardware', '07 · M3 紧固件及嵌件（示意）')
    holes, checks = [], []
    for name, t, x, y in locations:
        theta = t
        while theta < math.pi:
            theta += TAU
        levels = [height(theta+k*TAU) for k in range(3)] if name != 'C' else []
        posts = mounts.post_parts(levels) if levels else mounts.sign_post_parts()
        for p in posts:
            source = 'garage-bookshelf v5 BRep snapshot' if p['role'] in ('post-standard', 'post-cap') else 'Approved column reuse concept'
            feature(f'{name}_{p["name"]}', mounts.transformed(p['shape'], t, (x, y, 0)), p['role'], BLACK, parent, source=source)
        for p in mounts.foot_hardware():
            feature(f'{name}_{p["name"]}', mounts.transformed(p['shape'], t, (x, y, 0)), p['role'], p['color'], hardware)
        if not levels:
            continue
        post = compound([p['shape'] for p in posts])
        for k, h in enumerate(levels):
            parts = mounts.station(theta+k*TAU, height)
            # Provide 0.05-mm beam clearance at the independently lofted
            # road underside. The root tab still bears directly on its collar.
            # Underside screws close this small assembly allowance on tightening.
            clearance = P['arm_beam_clearance']
            beam = mounts.old.arm_loft(theta+k*TAU, height)
            beam.translate(V(0, 0, -clearance))
            arm = beam.cut(mounts.cyl(10, -35, mounts.TAB_BOTTOM))
            arm = arm.fuse(mounts.cyl(10, mounts.TAB_BOTTOM, mounts.TAB_TOP))
            arm = arm.cut(mounts.cyl(3.25, mounts.TAB_BOTTOM-1, mounts.TAB_TOP+1))
            derivative = (height(theta+1e-5)-height(theta-1e-5))/(2e-5)
            for index, radius in enumerate((110, 145), 1):
                slope = derivative/radius
                normal = V(0, -slope, 1)
                normal.normalize()
                p = V(radius-169, 0, -THICK)
                arm = arm.cut(Part.makeCylinder(1.7, 18, p-normal*12, normal))
                shift = -normal*(clearance/math.sqrt(1+slope*slope))
                for item in parts:
                    if item['name'] in (f'road_washer_{index}', f'road_bolt_{index}'):
                        item['shape'].translate(shift)
            next(item for item in parts if item['role'] == 'arm')['shape'] = arm.removeSplitter()
            check = mounts.interference_checks(parts, post, h)
            check.update(station=name, level=k+1, road_z=h)
            checks.append(check)
            for p in parts:
                if p['role'] == 'road':
                    continue
                target = parent if p['role'] == 'arm' else hardware
                feature(f'{name}_Level{k+1}_{p["name"]}', mounts.transformed(p['shape'], t, (x, y, h)),
                        p['role'], p['color'], target, source='Approved column reuse concept')
            for r in (110, 145):
                derivative = (height(theta+1e-5)-height(theta-1e-5))/(2e-5)
                normal = V(0, -derivative/r, 1)
                normal.normalize()
                # Start the tool outside the bottom surface. A cap coincident
                # with that spline surface creates unstable STEP healing.
                lead = .5
                hole = Part.makeCylinder(P['road_pilot_diameter']/2, P['road_pilot_depth']+lead,
                                         V(r-169, 0, -THICK)-normal*lead, normal)
                holes.append(mounts.transformed(hole, t, (x, y, h)))
    tool = feature('Road_BlindHole_Tools', compound(holes), 'construction', parent=group('Construction', '90 · 道路放样截面（隐藏）'), final=False)
    road = DOC.addObject('Part::Cut', 'Road_Continuous_18BlindHoles')
    road.Base, road.Tool = roadway, tool
    road.Refine = True
    metadata(road, 'road', BLACK)
    group('Road', '02 · 连续主道路').addObject(road)
    DOC.recompute()
    assert road.Shape.isValid() and len(road.Shape.Solids) == 1
    return road, checks


def text_shape(value, size, origin, rot=None, thickness=None, max_width=None):
    strings = Part.makeWireString(value, FONT, size, 0)
    chars = [Part.makeFace(c, 'Part::FaceMakerBullseye').extrude(V(0, 0, thickness or P['text_thickness'])) for c in strings if c]
    sh = compound(chars)
    if max_width is not None and sh.BoundBox.XLength > max_width:
        sh.scale(max_width/sh.BoundBox.XLength)
    if rot:
        sh.Placement.Rotation = rot
    sh.translate(V(*origin))
    return sh


def build_decoration():
    parent = group('Decoration', '06 · 车位标识与广告牌')
    text_group = group('Lettering', '08 · 实体文字与编号')
    marking = P['marking_thickness']
    for k, z in enumerate(P['floor_z']):
        white, cyan, blue = [], [], []
        bounds = [20, 118, 180] if k < 2 else [20, 73.333, 126.667, 180]
        for j, (a, b) in enumerate(zip(bounds, bounds[1:])):
            for x in (a+3, b-3):
                white.append(mounts.box(x-.6, x+.6, 124, 214, z, z+marking))
            white.append(mounts.box(a+3, b-3, 213, 214, z, z+marking))
            feature(f'BayNumber_{k+1}_{j+1}', text_shape(str((k+1)*100+j+1), 4, (a+7, 113, z)), 'lettering', WHITE, text_group)
        if k < 2:
            blue.append(mounts.box(22, 49, 126, 211, z, z+.08))
            feature(f'ParkingP_{k+1}', text_shape('P', 6, (26, 113, z)), 'lettering', WHITE, text_group)
        for y in range(127, 211, 9):
            for a, b in ((3, 16), (184, 197)):
                cyan.append(polygon_solid([(a, y, z), (b, y+4, z), (b, y+5.3, z), (a, y+1.3, z)], marking))
        for y in range(37, 103, 9):
            white.append(mounts.box(20, 39, y, y+3, z, z+marking))
        white.append(polygon_solid([(73, 72, z), (138, 72, z), (138, 67, z), (152, 75, z),
                                    (138, 83, z), (138, 78, z), (73, 78, z)], marking))
        # Union intersecting U-shaped line corners within each color.
        feature(f'ParkingMarks_{k+1}F_White', white[0].multiFuse(white[1:]).removeSplitter(), 'parking-mark', WHITE, parent)
        feature(f'ParkingMarks_{k+1}F_Cyan', compound(cyan), 'parking-mark', CYAN, parent)
        if blue:
            feature(f'ParkingMarks_{k+1}F_Blue', compound(blue), 'parking-mark', BLUE, parent)
        trim = BLACK if k == 0 else PALETTE[k-1]
        feature(f'FrontTrim_{k+1}F', mounts.box(0, 200, -.6, 0, z-3, z), 'trim', trim, parent)
        if k:
            feature(f'FloorLabelPlate_{k+1}', mounts.box(157, 193, -2, -.7, z-17, z-1), 'sign', BLACK, parent)
            feature(f'FloorLabel_{k+1}', text_shape(f'{k+1}F', 9, (161, -2, z-14), App.Rotation(V(1, 0, 0), 90)), 'lettering', WHITE, text_group)
        else:
            feature('FloorLabel_1', text_shape('1F', 4, (158, -.6, 1), App.Rotation(V(1, 0, 0), 90)), 'lettering', WHITE, text_group)
    # Posts seat on the wall at Z=232 and terminate at the sign bottom Z=263.
    for x, color in ((28, CYAN), (151, RED)):
        feature(f'BillboardPost_{x}', mounts.box(x, x+15, 230, 234, 232, 263), 'sign', color, parent)
    feature('TopBillboard', mounts.box(0, 196, 226, 234, 263, 319), 'sign', BLACK, parent)
    front = App.Rotation(V(1, 0, 0), 90)
    feature('TopBillboard_Text1', text_shape('Lovely Cars', 16, (15, 226, 293), front, max_width=172), 'lettering', WHITE, text_group)
    feature('TopBillboard_Text2', text_shape("I've Driven", 16, (15, 226, 270), front, max_width=172), 'lettering', WHITE, text_group)
    # A recessed panel and matching back cutout make the separate sign colors
    # non-overlapping; the column is socketed through the frame behind it.
    frame = mounts.box(588, 619, 63, 69, 107, 241)
    frame = frame.cut(mounts.box(590, 617, 62, 64, 109, 239))
    sign_column = compound([o.Shape for o in FINAL if o.Name.startswith('C_') and o.DesignRole in ('post-standard', 'post-cap', 'spacer')])
    frame = frame.cut(sign_column).removeSplitter()
    feature('SideSignFrame', frame, 'sign', BLACK, parent)
    feature('SideSignBlue', mounts.box(590, 617, 63, 64, 109, 239), 'sign', BLUE, parent)
    # local X -> -Z, local Y -> +X, outward normal -> -Y.
    side_rot = App.Rotation(V(0, 0, -1), V(1, 0, 0), V(0, -1, 0), 'ZXY')
    for x, value in ((593, 'HORSEPOWER LEFT,'), (606, 'BRAINPOWER RIGHT')):
        feature(f'SideText_{x}', text_shape(value, 6, (x, 63, 230), side_rot, max_width=118), 'lettering', WHITE, text_group)
    # Curved arrow outlines lie on the actual slope; narrow planar strips are
    # projected into the road's top surface, then offset by 0.12 mm in Z.
    for k in range(3):
        for j, u in enumerate((.24, .72)):
            t = math.pi+TAU*(k+u)
            outline = [(-1.3, -12), (1.3, -12), (1.3, 3), (5, 3), (0, 13), (-5, 3), (-1.3, 3)]
            # Triangulated top/bottom faces give a closed solid even though
            # the seven contour vertices lie at different road heights.
            vs = [point(120+dr, t+along/120, height(t+along/120)+.03) for dr, along in outline]
            faces = []
            # Outline consists of a rectangle and triangle sharing one edge.
            for indexes in ((0, 1, 2, 6), (6, 2, 3, 4, 5)):
                pts = [vs[i] for i in indexes]
                # A ruled loft between top and bottom polygon wires supports
                # non-planar outlines through a triangle fan shell.
                center = sum(pts, V())/len(pts)
                for a, b in zip(pts, pts[1:]+pts[:1]):
                    faces.append(Part.Face(Part.makePolygon([center, a, b, center])))
            top = Part.makeShell(faces)
            # Native face extrusion and union; the individual triangles are
            # solids and can be reviewed independently in the saved BRep.
            solids = [f.extrude(V(0, 0, marking)) for f in top.Faces]
            feature(f'RoadArrow_{k+1}_{j+1}', solids[0].multiFuse(solids[1:]).removeSplitter(), 'road-mark', WHITE, parent)


def main():
    global DOC
    started = time.time()
    (ROOT/'cad').mkdir(exist_ok=True)
    (ROOT/'reports').mkdir(exist_ok=True)
    DOC = App.newDocument('ParkingLotV1')
    DOC.Label = 'Parking Lot · CAD v1'
    DOC.Comment = 'Four floors; 70 mm shared single lane; native smooth BRep roadway. Assembly design v1, track segmentation and print joints pending.'
    sheet()
    log('Building native road lofts and exact circular landings')
    roadway = build_road()
    log('Building foundation, native deck pads/pockets and original columns')
    locations = build_garage()
    log('Building reused support stacks, arms and 18 blind mounting holes')
    road, support_checks = build_supports(locations, roadway)
    log('Building solid markings and signs')
    build_decoration()
    DOC.recompute()
    for obj in FINAL:
        assert obj.Shape.isValid(), obj.Name
    sketches = [o for o in DOC.Objects if o.TypeId == 'Sketcher::SketchObject']
    assert all(o.FullyConstrained for o in sketches), [o.Name for o in sketches if not o.FullyConstrained]
    for obj in FINAL:
        MANIFEST.append(dict(name=obj.Name, label=obj.Label, role=obj.DesignRole,
                             color=list(obj.DesignColor[:3]), solids=len(obj.Shape.Solids),
                             volume_mm3=obj.Shape.Volume, source=obj.GeometrySource))
    native = ROOT/'cad/parking-lot-v1-assembly.FCStd'
    DOC.recompute()
    DOC.saveAs(str(native))
    log('Exporting complete STEP assembly')
    Part.export(FINAL, str(ROOT/'cad/parking-lot-v1-assembly.step'))
    (ROOT/'reports/parts.json').write_text(json.dumps(MANIFEST, ensure_ascii=False, indent=2)+'\n')
    dependencies = [ROOT/'parameters.json', Path(__file__),
                    CONCEPT/'installation/mount_parts.py', CONCEPT/'installation/column-reuse/column_parts.py',
                    CONCEPT/'installation/column-reuse/reference/garage-standard-column.brep',
                    CONCEPT/'installation/column-reuse/reference/garage-top-cap.brep']
    report = dict(status='built', units='mm', final_objects=len(FINAL),
                  native_sketches=len(sketches), fully_constrained_sketches=len(sketches),
                  native_road_lofts=3, road_connected_solids=len(road.Shape.Solids),
                  road_blind_holes=18, support_checks=support_checks,
                  dependencies=[dict(file=str(p.relative_to(ROOT.parent.parent)), sha256=sha(p)) for p in dependencies],
                  build_seconds=round(time.time()-started, 2),
                  scope='Assembly design CAD v1. Continuous track has no print segmentation or segment joints. Physical fit/load/vehicle turning untested.')
    (ROOT/'reports/build.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    App.closeDocument(DOC.Name)
    log(f'Built {len(FINAL)} visible objects, {len(sketches)} constrained sketches in {report["build_seconds"]} s')


if __name__ == '__main__':
    main()
