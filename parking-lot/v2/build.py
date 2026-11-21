"""Build the approved three-level CAD from native Garage Bookshelf solids.

Run run() in FreeCAD's Python console to save the native assembly and STEP.
All dimensions are in mm.
"""

from collections import Counter
from hashlib import sha256
import json
import math
from pathlib import Path
import shutil
import sys
import tempfile

import FreeCAD as App
import Part
import Sketcher

ROOT = Path(__file__).resolve().parent
BOOKSHELF = ROOT.parents[1] / 'garage-bookshelf/v5'
SOURCE = BOOKSHELF / 'cad/garage-bookshelf-v5-assembly.FCStd'
sys.path.insert(0, str(BOOKSHELF / 'src'))

from garage_bookshelf.assembly import global_shape
from garage_bookshelf.rendering.software import saved_colors

V = App.Vector
HALF_DECK = 97.8
TURN_RADIUS = 60.0
LEAD_LENGTH = 55.0
PORT_OFFSET = 40.0
LANE = 34.0
SLAB = 5.0
RAIL = 2.34
RAIL_HEIGHT = 3.75
PEDESTAL_RADIUS = 10.3
POST_RADIUS = 6.8
FOOT_CLEARANCE = 3.0
FLOORS = (6.6, 69.6, 132.6)
BLACK = (22/255, 24/255, 27/255)
ROAD = (25/255, 28/255, 32/255)
CYAN = (57/255, 169/255, 219/255)
RED = (237/255, 36/255, 42/255)
DECKS = [f'garage_deck_{i}_Body' for i in range(1, 4)]
COLUMNS = [f'column_{i}_segment_{j}_Body' for i in range(1, 5) for j in (2, 3, 4)]
BASENAME = 'parking-lot-v2-assembly'


def source_parts():
    with tempfile.TemporaryDirectory() as tmp:
        # Read a private copy so the user's source document is never opened or saved.
        snapshot = Path(tmp) / SOURCE.name
        shutil.copyfile(SOURCE, snapshot)
        digest = sha256(snapshot.read_bytes()).hexdigest()
        colors = saved_colors(snapshot)
        source = App.openDocument(str(snapshot))
        try:
            bounds = global_shape(source.getObject(DECKS[0])).BoundBox
            origin = V((bounds.XMin+bounds.XMax)/2, (bounds.YMin+bounds.YMax)/2, bounds.ZMin)
            parts = {}
            for name in DECKS + COLUMNS:
                body = source.getObject(name)
                shape = global_shape(body)
                shape.translate(-origin)
                rgb = colors.get(body.Tip.Name, colors.get(body.Name))
                assert rgb and len(rgb) in (1, len(shape.Faces)), name
                if len(rgb) == 1:
                    rgb = rgb * len(shape.Faces)
                parts[name] = (shape, rgb)
        finally:
            App.closeDocument(source.Name)
    return parts, digest


def group(doc, name, label):
    obj = doc.addObject('App::DocumentObjectGroup', name)
    obj.Label = label
    return obj


def solid(doc, parent, name, label, shape):
    obj = doc.addObject('Part::Feature', name)
    obj.Label = label
    obj.Shape = shape
    parent.addObject(obj)
    return obj


def plan_stations():
    """Return plan points, tangent vectors and cumulative chord lengths."""
    def lead(u):
        return u**3 * (10 + u * (-15 + 6*u))

    spread = TURN_RADIUS - PORT_OFFSET
    stations = []
    for i in range(17):
        u = i/16
        stations.append((HALF_DECK + LEAD_LENGTH*u, -PORT_OFFSET - spread*lead(u),
                         LEAD_LENGTH, -spread*30*u**2*(1-u)**2))
    for i in range(1, 49):
        a = -math.pi/2 + math.pi*i/48
        stations.append((HALF_DECK + LEAD_LENGTH + TURN_RADIUS*math.cos(a),
                         TURN_RADIUS*math.sin(a), -math.sin(a), math.cos(a)))
    for i in range(1, 17):
        u = 1-i/16
        stations.append((HALF_DECK + LEAD_LENGTH*u, PORT_OFFSET + spread*lead(u),
                         -LEAD_LENGTH, -spread*30*u**2*(1-u)**2))
    lengths = [0.]
    for a, b in zip(stations, stations[1:]):
        lengths.append(lengths[-1] + math.dist(a[:2], b[:2]))
    return stations, lengths


def climb(fraction, rise):
    ease = .125
    if fraction < ease:
        height = fraction**2/(2*ease)
    elif fraction > 1-ease:
        height = 1-ease - (1-fraction)**2/(2*ease)
    else:
        height = fraction-ease/2
    return rise*height/(1-ease)


def outboard_pedestal(doc, parent, construction, road, prefix, label, side, top):
    turn_apex = HALF_DECK + LEAD_LENGTH + TURN_RADIUS
    outer_edge = turn_apex + LANE/2 + RAIL
    center = outer_edge + FOOT_CLEARANCE + PEDESTAL_RADIUS
    foot = Part.makeCylinder(PEDESTAL_RADIUS, 2.6, V(side*center, 0, 0))
    stem = Part.makeCylinder(POST_RADIUS, top, V(side*center, 0, 0))
    column = solid(doc, construction, f'{prefix}Column', label+' · 外移立柱及柱脚',
                   foot.fuse(stem).removeSplitter())
    # A tapered 12 mm corbel transfers the load from the road to the post.
    # Its tip is cut by the same ramp solid to seat against the curved underside.
    inner = turn_apex + 3
    outer = center + 3
    profile = [(inner, top), (outer, top), (outer, top-20), (inner, top-8)]
    vertices = [V(side*x, -6, z) for x, z in profile]
    corbel = Part.Face(Part.makePolygon(vertices+vertices[:1])).extrude(V(0, 12, 0))
    arm = solid(doc, construction, f'{prefix}Corbel', label+' · 坡底托臂毛坯', corbel)
    stock = doc.addObject('Part::MultiFuse', f'{prefix}PedestalStock')
    stock.Label = label+' · 支座毛坯'
    stock.Shapes = [column, arm]
    stock.Refine = True
    construction.addObject(stock)
    pedestal = doc.addObject('Part::Cut', f'{prefix}Pedestal')
    pedestal.Label = label+' · 外置圆柱与托臂'
    pedestal.Base, pedestal.Tool = stock, road
    pedestal.Refine = True
    parent.addObject(pedestal)
    return pedestal


def ramp(doc, parent, construction, side, start, end):
    stations, lengths = plan_stations()
    label = '右侧 1F → 2F' if side == 1 else '左侧 2F → 3F'
    prefix = 'Right' if side == 1 else 'Left'
    a, b = LANE/2, LANE/2 + RAIL
    profile = [(-b, -SLAB), (b, -SLAB), (b, RAIL_HEIGHT), (a, RAIL_HEIGHT),
               (a, 0.), (-a, 0.), (-a, RAIL_HEIGHT), (-b, RAIL_HEIGHT)]
    points = [V(x, y, 0) for x, y in profile]
    geometry = [Part.LineSegment(p, q) for p, q in zip(points, points[1:]+points[:1])]
    profiles = []
    for i, ((x, y, dx, dy), length) in enumerate(zip(stations, lengths)):
        d = math.hypot(dx, dy)
        u, v = V(side*dy/d, -dx/d, 0), V(0, 0, 1)
        section = doc.addObject('Sketcher::SketchObject', f'{prefix}Section{i:02}')
        section.Label = f'{label} · 截面 {i:02}'
        section.Placement = App.Placement(V(side*x, y, start+climb(length/lengths[-1], end-start)),
                                          App.Rotation(u, v, u.cross(v), 'XYZ'))
        section.addGeometry(geometry, False)
        section.addConstraint([Sketcher.Constraint('Block', j) for j in range(len(geometry))])
        construction.addObject(section)
        profiles.append(section)
    lofts = []
    for title, lo, hi in [('入口', 0, 16), ('半圆', 16, 64), ('出口', 64, 80)]:
        loft = doc.addObject('Part::Loft', f'{prefix}Loft')
        loft.Label = f'{label} · {title}放样'
        loft.Sections = profiles[lo:hi+1]
        loft.MaxDegree = 3
        loft.Solid = True
        loft.Ruled = False
        construction.addObject(loft)
        lofts.append(loft)
    road = doc.addObject('Part::MultiFuse', f'{prefix}Ramp')
    road.Label = f'{label} · 连续坡道与护栏'
    road.Shapes = lofts
    road.Refine = True
    parent.addObject(road)
    for key, value in [('LaneWidth', LANE), ('TurnRadius', TURN_RADIUS), ('Rise', end-start),
                       ('PlanCenterlineLength', lengths[-1])]:
        road.addProperty('App::PropertyLength', key, 'Geometry reference')
        setattr(road, key, value)
        road.setEditorMode(key, 1)
    pedestal = outboard_pedestal(doc, parent, construction, road, prefix, label, side,
                                  (start+end)/2-1.65)
    return road, pedestal


def ramp_colors(road, accent):
    # Keep the running surface, underside and end faces dark. Six of the
    # eight longitudinal faces of each loft belong to the two integral rails.
    rails = []
    for loft in road.Shapes:
        assert len(loft.Shape.Faces) == 10, loft.Name
        rails.extend(loft.Shape.Faces[i] for i in (1, 2, 3, 5, 6, 7))
    colors = []
    for face in road.Shape.Faces:
        match = any(abs(face.Area-other.Area) < 1e-4 and
                    (face.CenterOfMass-other.CenterOfMass).Length < 1e-4 for other in rails)
        colors.append(accent if match else ROAD)
    assert colors.count(accent) == 18, road.Name
    return colors


def assemble(parts, digest):
    doc = App.newDocument('ParkingLotV2')
    doc.Label = 'Parking Lot v2 · 三层车库'
    doc.Comment = ('Approved three-level concept. Garage Bookshelf v5 source SHA256: '+digest)
    decks = group(doc, 'Decks', '01 · 原版停车板')
    columns = group(doc, 'Columns', '02 · 原版圆柱')
    right = group(doc, 'RightSide', '03 · 右侧坡道与支座')
    left = group(doc, 'LeftSide', '04 · 左侧坡道与支座')
    construction = group(doc, 'Construction', '90 · 放样截面与毛坯')
    finished = {}
    colors = {}
    for i, name in enumerate(DECKS, 1):
        shape, rgb = parts[name]
        obj = solid(doc, decks, name, f'{i}F · 原版停车板', shape)
        colors[obj.Name] = rgb
        finished[obj.Name] = obj
    for name in COLUMNS:
        shape, rgb = parts[name]
        pos, segment = name.split('_')[1:4:2]
        label = f'{pos}号柱 · ' + ('原版柱帽' if segment=='4' else f'原版柱段 {segment}')
        obj = solid(doc, columns, name, label, shape)
        colors[obj.Name] = rgb
        finished[obj.Name] = obj
    for parent, side, i, accent in [(right, 1, 0, CYAN), (left, -1, 1, RED)]:
        road, support = ramp(doc, parent, construction, side, FLOORS[i], FLOORS[i+1])
        finished.update({obj.Name: obj for obj in (road, support)})
        doc.recompute()
        colors[road.Name] = ramp_colors(road, accent)
        colors[support.Name] = [BLACK]*len(support.Shape.Faces)
    return doc, finished, colors


def signature(shape):
    b = shape.optimalBoundingBox(False, False)
    return [shape.Volume, b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax, len(shape.Faces)]


def verify_geometry(finished, parts):
    checks = []
    for name, obj in finished.items():
        shape = obj.Shape
        assert shape.isValid() and len(shape.Solids)==1 and shape.isClosed(), name
        if name in parts:
            assert all(abs(a-b)<1e-5 for a,b in zip(signature(shape),signature(parts[name][0]))), name
    for side, prefix, i in [(1,'Right',0),(-1,'Left',1)]:
        road = finished[prefix+'Ramp'].Shape
        pedestal = finished[prefix+'Pedestal']
        support = pedestal.Shape
        b = road.optimalBoundingBox(False, False)
        near_edge = b.XMin if side==1 else -b.XMax
        assert abs(near_edge-HALF_DECK)<.002, (prefix, b)
        expected_volume = ((LANE+2*RAIL)*SLAB + 2*RAIL*RAIL_HEIGHT)*plan_stations()[1][-1]
        assert abs(road.Volume-expected_volume)/expected_volume<.003, prefix
        # A planar intersection at each mouth verifies a full butt-face mate.
        x = side*HALF_DECK
        for j, y in [(i,-PORT_OFFSET),(i+1,PORT_OFFSET)]:
            deck = finished[DECKS[j]].Shape
            z = deck.BoundBox.ZMax
            end = next(f for f in road.Faces if f.BoundBox.XLength<1e-5
                       and abs(f.CenterOfMass.y-y)<1e-5)
            points = [v.Point for v in end.Vertexes]
            top = [p for p in points if abs(abs(p.y-y)-LANE/2)<1e-5 and abs(p.z-z)<1e-5]
            assert len(top)==2 and abs((top[0]-top[1]).Length-LANE)<1e-5, (prefix, j)
            contact = sum(end.common(f).Area for f in deck.Faces
                          if f.BoundBox.XLength<1e-5 and abs(f.CenterOfMass.x-x)<1e-5)
            assert abs(contact-(LANE+2*RAIL)*SLAB)<.01, (prefix,j,contact)
            checks.append(dict(ramp=prefix, floor=j+1, xyz_mm=[x,y,z],
                               width_mm=LANE, step_mm=max(abs(p.z-z) for p in top),
                               contact_mm2=contact))
        gap = support.distToShape(road)[0]
        assert gap<1e-5 and abs(support.common(road).Volume)<.001, (prefix,gap)
        clearance = min(road.distToShape(finished[name].Shape)[0] for name in COLUMNS)
        assert clearance>1.0, (prefix,clearance)
        column = pedestal.Base.Shapes[0].Shape
        column_bounds = column.optimalBoundingBox(False, False)
        # A separating X interval proves zero XY overlap across the entire
        # swept ramp, even for a future ramp raised along the same plan path.
        projected_gap = (column_bounds.XMin-b.XMax if side==1
                         else b.XMin-column_bounds.XMax)
        assert abs(projected_gap-FOOT_CLEARANCE)<.002, (prefix,projected_gap)
        column_x = (column_bounds.XMin+column_bounds.XMax)/2
        checks.append(dict(ramp=prefix, minimum_column_clearance_mm=clearance,
                           pedestal_seat_gap_mm=gap,
                           support_column_center_xy_mm=[round(column_x, 3), 0.0],
                           support_foot_to_ramp_plan_gap_mm=round(projected_gap, 3),
                           support_column_plan_overlap=False))
    return checks


def run(output, preview=None):
    """Create, reopen and verify the colored FreeCAD assembly and STEP."""
    assert App.GuiUp, 'Run inside the FreeCAD application'
    import FreeCADGui as Gui
    import ImportGui

    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    native, step = output/(BASENAME+'.FCStd'), output/(BASENAME+'.step')
    report_path = output/'validation.json'
    if any(path.exists() for path in (native, step, report_path)):
        raise FileExistsError(f'Choose a new output directory: {output}')
    parts, digest = source_parts()
    doc, objects, colors = assemble(parts, digest)
    verify_geometry(objects, parts)
    for obj in doc.Objects:
        obj.ViewObject.Visibility = obj.Name in objects or (
            obj.TypeId=='App::DocumentObjectGroup' and obj.Name!='Construction')
        if obj.Name in colors:
            rgb = colors[obj.Name]
            obj.ViewObject.ShapeColor = rgb[0]
            obj.ViewObject.DiffuseColor = rgb
            obj.ViewObject.DisplayMode = 'Shaded'
            obj.ViewObject.Deviation = .10
    App.setActiveDocument(doc.Name)
    view = Gui.activeDocument().activeView()
    toward = V(.50,-.84,.46)
    toward.normalize()
    right = V(0,0,1).cross(toward)
    right.normalize()
    view.setCameraOrientation(App.Rotation(right, toward.cross(right), toward, 'ZXY').Q)
    view.fitAll()
    doc.recompute()
    doc.saveAs(str(native))
    ImportGui.export(list(objects.values()), str(step))
    App.closeDocument(doc.Name)
    reopened = App.openDocument(str(native))
    copied = {name: reopened.getObject(name) for name in objects}
    checks = verify_geometry(copied, parts)
    saved = saved_colors(native)
    for name, expected in colors.items():
        actual = saved[name]
        if len(actual)==1:
            actual = actual*len(expected)
        assert len(actual)==len(expected) and all(
            max(abs(a-b) for a,b in zip(p,q)) <= 1/255 + 1e-8
            for p,q in zip(actual,expected)), name
    imported = Part.Shape()
    imported.read(str(step))
    assert imported.isValid() and len(imported.Solids)==len(copied)
    original = sorted(obj.Shape.Volume for obj in copied.values())
    received = sorted(s.Volume for s in imported.Solids)
    assert all(s.isClosed() for s in imported.Solids)
    assert all(abs(a-b)<max(.05, a*3e-6) for a,b in zip(original,received))
    assert 'COLOUR_RGB' in step.read_text(), 'STEP appearance data missing'
    assert sha256(SOURCE.read_bytes()).hexdigest()==digest
    if preview:
        Gui.activeDocument().activeView().saveImage(str(preview), 1600, 1000, 'White')
    report = dict(status='passed', solids=len(received), source_parts=len(parts), source_sha256=digest,
                  lofts=6, sketches=162, deck_dimensions_mm=[195.6,158.6,6.6],
                  design_colors_verified=True, step_valid=True, step_contains_colors=True,
                  interface_checks=checks)
    report_path.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)
