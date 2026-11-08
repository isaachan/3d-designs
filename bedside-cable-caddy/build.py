"""Build the bedside cable caddy using FreeCAD's bundled Python."""

import json
import math
import os
from pathlib import Path
import sys

FREECAD = Path(os.environ.get("FREECAD_RESOURCES", "/Applications/FreeCAD.app/Contents/Resources"))
sys.path.insert(0, str(FREECAD / "lib"))
import FreeCAD as App
import Mesh
import MeshPart
import Part

ROOT = Path(__file__).resolve().parent
NAME = "bedside-cable-caddy"
WIDTH = 208
DEPTH = 64
HEIGHT = 98
FRONT_HEIGHT = 46
BACK = 4.4
SIDE = 3.4
FRONT = 3.2
FLOOR = 3.6
CORNER = 7
FRONT_SLOTS = (-61, 0, 61)
VENT_COLUMNS = (-78, -52, -26, 0, 26, 52, 78)
VENT_ROWS = (22, 42)
TAPE_CENTERS = (-67, 67)
TAPE_WIDTH = 25
TAPE_HEIGHT = 80
TAPE_BOTTOM = 9
V = App.Vector


def wire_from_points(points):
    return Part.makePolygon(points + [points[0]])


def bezier(points):
    curve = Part.BezierCurve()
    curve.setPoles(points)
    return curve.toShape()


def rounded_plan(left, back, right, front, radius, z):
    """CCW plan wire with tangent circular corners."""
    corners = (
        (right - radius, back + radius, -90),
        (right - radius, front - radius, 0),
        (left + radius, front - radius, 90),
        (left + radius, back + radius, 180),
    )
    arcs = []
    for x, y, angle in corners:
        circle = Part.Circle(V(x, y, z), V(0, 0, 1), radius)
        arcs.append(Part.ArcOfCircle(circle, math.radians(angle), math.radians(angle + 90)).toShape())
    edges = []
    for index, arc in enumerate(arcs):
        edges.append(arc)
        edges.append(Part.makeLine(arc.Vertexes[-1].Point, arcs[(index + 1) % 4].Vertexes[0].Point))
    return Part.Face(Part.Wire(edges))


def profile(width=WIDTH, height=HEIGHT, front_height=FRONT_HEIGHT, depth=DEPTH):
    def p(y, z):
        return V(-width / 2 - 1, y, z)

    rear = p(-1, height)
    shoulder = p(9, height)
    slope_start = p(20, front_height + 36)
    slope_end = p(36, front_height + 4)
    nose = p(46, front_height)
    front = p(depth + 1, front_height)
    return Part.Face(Part.Wire([
        Part.makeLine(rear, shoulder),
        bezier([shoulder, p(14, height), p(16, front_height + 44), slope_start]),
        Part.makeLine(slope_start, slope_end),
        bezier([slope_end, p(38, front_height), p(42, front_height), nose]),
        Part.makeLine(nose, front),
        Part.makeLine(front, p(depth + 1, -1)),
        Part.makeLine(p(depth + 1, -1), p(-1, -1)),
        Part.makeLine(p(-1, -1), rear),
    ])).extrude(V(width + 2, 0, 0))


def cable_slot(point, center, radius, low, direction, height=HEIGHT):
    """An open U with a round root. The cable drops in from above."""
    left, right = center - radius, center + radius
    top = height + 2
    arc = Part.Arc(point(left, low), point(center, low - radius), point(right, low)).toShape()
    return Part.Face(Part.Wire([
        arc,
        Part.makeLine(point(right, low), point(right, top)),
        Part.makeLine(point(right, top), point(left, top)),
        Part.makeLine(point(left, top), point(left, low)),
    ])).extrude(direction)


def air_slot(x, y):
    radius = 2.5
    offset = 8.5
    left, right = x - offset, x + offset
    z = -1
    edge = Part.makeLine
    arc = Part.Arc
    return Part.Face(Part.Wire([
        edge(V(left, y - radius, z), V(right, y - radius, z)),
        arc(V(right, y - radius, z), V(right + radius, y, z), V(right, y + radius, z)).toShape(),
        edge(V(right, y + radius, z), V(left, y + radius, z)),
        arc(V(left, y + radius, z), V(left - radius, y, z), V(left, y - radius, z)).toShape(),
    ])).extrude(V(0, 0, FLOOR + 2))


def rib(y):
    # 45 degree shoulders, 1.6 mm flat top. The adapter sits above the vents.
    left = -91
    section = wire_from_points([
        V(left, y - 2.8, FLOOR - 0.2),
        V(left, y + 2.8, FLOOR - 0.2),
        V(left, y + 0.8, FLOOR + 1.8),
        V(left, y - 0.8, FLOOR + 1.8),
    ])
    return Part.Face(section).extrude(V(182, 0, 0))


def build():
    half = WIDTH / 2
    outside = rounded_plan(-half, 0, half, DEPTH, CORNER, 0).extrude(V(0, 0, HEIGHT + 1))
    inside = rounded_plan(-half + SIDE, BACK, half - SIDE, DEPTH - FRONT, 4, FLOOR)
    cavity = inside.extrude(V(0, 0, HEIGHT))
    shell = outside.cut(cavity).common(profile()).removeSplitter()

    # Select the two rim loops, including the swept sections along the sides.
    # Bottom-up printing keeps the large wall face off the build plate.
    rim = [edge for edge in shell.Edges if edge.BoundBox.ZMin >= FRONT_HEIGHT - 1e-6
           and edge.BoundBox.ZMax - edge.BoundBox.ZMin < HEIGHT - FRONT_HEIGHT + 1e-6]
    shell = shell.makeFillet(0.65, rim).removeSplitter()

    slots = [
        cable_slot(lambda x, z: V(x, DEPTH - FRONT - 1, z), x, 5, 37, V(0, FRONT + 2, 0))
        for x in FRONT_SLOTS
    ]
    slots += [
        cable_slot(lambda y, z: V(x, y, z), 21, 7, 65, V(SIDE + 2, 0, 0))
        for x in (-half - 1, half - SIDE - 1)
    ]
    shell = shell.cut(slots).removeSplitter()
    vents = [air_slot(x, y) for x in VENT_COLUMNS for y in VENT_ROWS]
    floor = shell.cut(vents)
    return floor.fuse([rib(y) for y in (12, 32, 52)]).removeSplitter()


def near(value, expected, tolerance=1e-5):
    assert abs(value - expected) < tolerance, (value, expected)


def check_shape(shape):
    assert shape.isValid() and shape.isClosed() and len(shape.Solids) == 1
    bounds = shape.optimalBoundingBox(False, False)
    for length, expected in zip((bounds.XLength, bounds.YLength, bounds.ZLength), (WIDTH, DEPTH, HEIGHT)):
        near(length, expected)
    near(bounds.ZMin, 0)
    for x in TAPE_CENTERS:
        # The entire rectangle must sit on the exact planar outside back face.
        left, right = x - TAPE_WIDTH / 2, x + TAPE_WIDTH / 2
        bottom, top = TAPE_BOTTOM, TAPE_BOTTOM + TAPE_HEIGHT
        patch = Part.Face(wire_from_points([
            V(left, 0, bottom), V(right, 0, bottom), V(right, 0, top), V(left, 0, top),
        ]))
        near(patch.common(shape).Area, TAPE_WIDTH * TAPE_HEIGHT)
    fit_probe = Part.makeBox(193, 50, 30, V(-96.5, 7.5, FLOOR + 1.8))
    assert shape.common(fit_probe).Volume < 1e-6
    for x in FRONT_SLOTS:
        assert shape.isInside(V(x, DEPTH - FRONT / 2, 31.9), 1e-6, False)
        assert not shape.isInside(V(x, DEPTH - FRONT / 2, 32.1), 1e-6, False)
    for side in (-1, 1):
        x = side * (WIDTH / 2 - SIDE / 2)
        assert shape.isInside(V(x, 21, 57.9), 1e-6, False)
        assert not shape.isInside(V(x, 21, 58.1), 1e-6, False)
    for x in VENT_COLUMNS:
        for y in VENT_ROWS:
            probe = Part.makeCylinder(2.45, FLOOR + 2, V(x, y, -1))
            assert shape.common(probe).Volume < 1e-6


def main():
    shape = build()
    check_shape(shape)
    native = ROOT / "cad" / f"{NAME}.FCStd"
    step_path = ROOT / "cad" / f"{NAME}.step"
    stl = ROOT / "printing" / f"{NAME}.stl"

    doc = App.newDocument("BedsideCableCaddy")
    body = doc.addObject("Part::Feature", "Caddy")
    body.Label = "床头收纳盒 · 一体打印"
    body.Shape = shape
    doc.recompute()
    doc.saveAs(str(native))
    shape.exportStep(str(step_path))
    mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.06,
                                 AngularDeflection=0.10, Relative=False)
    mesh.write(str(stl))

    App.closeDocument(doc.Name)
    reopened = App.openDocument(str(native))
    native_shape = reopened.getObject("Caddy").Shape
    check_shape(native_shape)
    step = Part.Shape()
    step.read(str(step_path))
    check_shape(step)
    near(step.Volume, native_shape.Volume, 0.01)
    exported_mesh = Mesh.Mesh(str(stl))
    assert exported_mesh.isSolid() and exported_mesh.countComponents() == 1
    near(exported_mesh.Volume, native_shape.Volume, native_shape.Volume * 0.002)

    print(json.dumps({
        "dimensions_mm": [WIDTH, DEPTH, HEIGHT],
        "solid_volume_cm3": round(native_shape.Volume / 1000, 2),
        "stl_triangles": exported_mesh.CountFacets,
        "checks": ["native and STEP solid", "STL closed and connected", "floor vents",
                   "cable exits", "internal clearance", "planar tape areas"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
