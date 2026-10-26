"""Editable native profiles for gravity-seated parking trays, no magnets.

The uniform foot interface is independent of each vehicle's wheel restraints.
All profiles use dimensional expressions, without fixed/block constraints.
"""
import math

import FreeCAD as App
import Part
import Sketcher

from garage_bookshelf.assembly import group, part
from garage_bookshelf.geometry.features import finish, pad, pocket
from garage_bookshelf.geometry.sketches import plane, rectangle
from garage_bookshelf.parameters import evaluate, expression
from garage_bookshelf.parking.layout import center_ratio

LAYOUTS = {'module_1': 2, 'garage_deck_1': 2,
           'garage_deck_2': 3, 'garage_deck_3': 3}


def center_x(count, index):
    ratio = center_ratio(count,index)
    return f'({ratio:.15g})*DeckWidth'


def _dimension(sketch, kind, args, value):
    i = sketch.addConstraint(Sketcher.Constraint(kind, *args,
        evaluate(sketch.Document, value)))
    sketch.setExpression(f'Constraints[{i}]', expression(value))


def _line(sketch, start, end):
    doc = sketch.Document
    pts = [App.Vector(evaluate(doc, x), evaluate(doc, y), 0) for x, y in (start, end)]
    i = sketch.addGeometry(Part.LineSegment(*pts), False)
    for point, xy in enumerate((start, end), 1):
        for axis, value in zip(('X', 'Y'), xy):
            _dimension(sketch, 'Distance'+axis, (i, point), value)


def _arc(sketch, cx, cy, radius, quadrant):
    doc = sketch.Document
    circle = Part.Circle(App.Vector(evaluate(doc, cx), evaluate(doc, cy), 0),
                         App.Vector(0, 0, 1), evaluate(doc, radius))
    start = (quadrant-1)*math.pi/2
    i = sketch.addGeometry(Part.ArcOfCircle(circle, start, start+math.pi/2), False)
    _dimension(sketch, 'DistanceX', (i, 3), cx)
    _dimension(sketch, 'DistanceY', (i, 3), cy)
    _dimension(sketch, 'Radius', (i,), radius)
    for point, axis in ((1, 'X' if quadrant % 2 == 0 else 'Y'),
                        (2, 'Y' if quadrant % 2 == 0 else 'X')):
        _dimension(sketch, 'Distance'+axis, (i, point), cx if axis == 'X' else cy)


def rounded_profile(sketch, cx, cy, width, length, radius, finger=False):
    x0, x1 = f'({cx})-({width})/2', f'({cx})+({width})/2'
    y0, y1 = f'({cy})-({length})/2', f'({cy})+({length})/2'
    left, right = f'({x0})+({radius})', f'({x1})-({radius})'
    low, high = f'({y0})+({radius})', f'({y1})-({radius})'
    if finger:
        a, b = f'({cx})-ParkingFingerWidth/2', f'({cx})+ParkingFingerWidth/2'
        front = f'({y0})-ParkingFingerExtension'
        path = [(left, y0), (a, y0), (a, front), (b, front), (b, y0), (right, y0)]
        for p, q in zip(path, path[1:]):
            _line(sketch, p, q)
    else:
        _line(sketch, (left, y0), (right, y0))
    _arc(sketch, right, low, radius, 0)
    _line(sketch, (x1, low), (x1, high))
    _arc(sketch, right, high, radius, 1)
    _line(sketch, (right, y1), (left, y1))
    _arc(sketch, left, high, radius, 2)
    _line(sketch, (x0, high), (x0, low))
    _arc(sketch, left, low, radius, 3)


def recess_sketch(body, count, base=False):
    top = 'BaseThickness' if base else 'DeckThickness'
    sketch = plane(body, 'Sketch_ParkingTrayRecesses', offset=('Zero', 'Zero', top))
    sketch.Label = f'{count}个统一停车托座落座轮廓'
    shift = 'DeckEdgeGap+' if base else ''
    for i in range(count):
        rounded_profile(sketch, shift+center_x(count, i), shift+'ParkingCenterY',
            'ParkingRecessWidth', 'ParkingRecessLength', 'ParkingRecessRadius', True)
    body.Document.recompute()
    assert sketch.FullyConstrained, (sketch.Name, sketch.SolverMessages if hasattr(sketch, 'SolverMessages') else sketch.State)
    assert len(sketch.Shape.Wires) == count
    assert all(w.isClosed() for w in sketch.Shape.Wires)
    return sketch


def add_recesses(body, count, base=False, chamfer=True):
    sketch = recess_sketch(body, count, base)
    feature = pocket(body, 'Pocket_ParkingTrayRecesses', sketch, 'ParkingRecessDepth')
    feature.Label = f'停车托座浅槽 · {count}位 · 深1.6mm'
    if 'TrayRecessCount' not in body.PropertiesList:
        body.addProperty('App::PropertyInteger', 'TrayRecessCount', 'Parking trays')
        body.addProperty('App::PropertyString', 'TrayRecessNote', 'Parking trays')
    body.TrayRecessCount = count
    body.TrayRecessNote = '40x80mm通用底脚；单边0.3mm；重力落座，无磁铁；轮胎夹按车模适配'
    if not chamfer:
        return feature
    # Match complete projected edges to the native sketch, avoiding unrelated
    # parking glyphs and external edges after OCC topological renumbering.
    z = evaluate(body.Document, 'BaseThickness' if base else 'DeckThickness')
    min_z = z-evaluate(body.Document, 'DeckBlueDepth')
    edges = []
    for i, edge in enumerate(feature.Shape.Edges, 1):
        bb = edge.BoundBox
        if abs(bb.ZMax-bb.ZMin) > 1e-6 or bb.ZMin < min_z-1e-6:
            continue
        projected = edge.copy()
        projected.translate(App.Vector(0, 0, z-bb.ZMin))
        common = projected.common(sketch.Shape).Length
        if common >= edge.Length-1e-6:
            edges.append('Edge'+str(i))
    assert edges, body.Name
    bevel = body.newObject('PartDesign::Chamfer', 'Chamfer_ParkingTrayEntries')
    bevel.Label = '停车槽入口小倒角 · 0.2mm'
    bevel.Base = (feature, edges)
    bevel.setExpression('Size', expression('ParkingEntryChamfer'))
    bevel.Refine = True
    return finish(body, bevel)


def add_interface_sample(doc):
    samples = group(doc, 'ParkingTraySamples', '停车托座接口样件（默认隐藏，车型轮夹另配）')
    _, body = part(doc, samples, 'parking_tray_interface',
        '通用托座底脚样件 · 不含车型轮胎夹',
        (f'DeckEdgeGap+{center_x(3, 1)}', 'DeckEdgeGap+ParkingCenterY',
         'DeckZ3+DeckThickness-ParkingRecessDepth'))
    sketch = plane(body, 'Sketch_TrayFoot')
    rounded_profile(sketch, 'Zero', 'Zero', 'TrayFootWidth', 'TrayFootLength', 'TrayFootRadius')
    doc.recompute()
    assert sketch.FullyConstrained
    pad(body, 'Pad_TrayFoot', sketch, 'TrayPlateThickness')
    tab = rectangle(body, 'Sketch_TrayTab', 'TrayTabWidth', 'TrayTabProjection+0.5 mm',
        origin=('-TrayTabWidth/2', '-TrayFootLength/2-TrayTabProjection'))
    pad(body, 'Pad_TrayTab', tab, 'TrayPlateThickness')
    grip = rectangle(body, 'Sketch_TrayGrip', 'TrayTabWidth', 'TrayTabProjection+0.5 mm',
        origin=('-TrayTabWidth/2', '-TrayFootLength/2-TrayTabProjection'),
        offset=('Zero', 'Zero', 'TrayPlateThickness'))
    pad(body, 'Pad_TrayGrip', grip, 'TrayGripRise')
    body.addProperty('App::PropertyBool', 'VehicleRetentionComplete', 'Parking trays')
    body.VehicleRetentionComplete = False
    body.addProperty('App::PropertyString', 'InterfaceNote', 'Parking trays')
    body.InterfaceNote = '仅通用底脚与取放耳；未给未知车型设计轮胎扣；样件不代表完整车模固定器'
    return body
