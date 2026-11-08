"""Build and check the V2 three-pocket wall cable module."""

import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
from build import App, BACK, CORNER, DEPTH, FLOOR, FRONT, Mesh, MeshPart, Part, SIDE, V
from build import bezier, cable_slot, near, profile, rounded_plan, wire_from_points

NAME = "bedside-cable-tray"
WIDTH = 232
HEIGHT = 126
FRONT_HEIGHT = 74
DIVIDER = 3.2
POCKET = (WIDTH - 2 * SIDE - 2 * DIVIDER) / 3
PITCH = POCKET + DIVIDER
CENTERS = (-PITCH, 0, PITCH)
TAPE_WIDTH = 25
TAPE_HEIGHT = 90
TAPE_CENTERS = (-80, 80)
TAPE_Z = 18
FIT = (66, 52, 112)
LOOP = (60, 104)
CABLE_CASES = ((2, 6), (3, 4))


def partition(center):
    def p(y, z):
        return V(center - DIVIDER / 2, y, z)

    back = p(BACK - 0.5, 105)
    high = p(15, 105)
    low = p(47, 68)
    front = p(DEPTH - FRONT + 0.5, 68)
    bottom_front = p(DEPTH - FRONT + 0.5, FLOOR - 0.5)
    bottom_back = p(BACK - 0.5, FLOOR - 0.5)
    boundary = Part.Wire([
        Part.makeLine(back, high),
        bezier([high, p(27, 105), p(31, 68), low]),
        Part.makeLine(low, front),
        Part.makeLine(front, bottom_front),
        Part.makeLine(bottom_front, bottom_back),
        Part.makeLine(bottom_back, back),
    ])
    divider = Part.Face(boundary).extrude(V(DIVIDER, 0, 0))
    top_edges = [edge for edge in divider.Edges if edge.BoundBox.ZMin >= 68 - 1e-6]
    return divider.makeFillet(0.7, top_edges)


def build():
    half = WIDTH / 2
    outside = rounded_plan(-half, 0, half, DEPTH, CORNER, 0).extrude(V(0, 0, HEIGHT + 1))
    inside = rounded_plan(-half + SIDE, BACK, half - SIDE, DEPTH - FRONT, 4, FLOOR)
    cavity = inside.extrude(V(0, 0, HEIGHT))
    shell = outside.cut(cavity).common(profile(WIDTH, HEIGHT, FRONT_HEIGHT)).removeSplitter()
    rim = [edge for edge in shell.Edges if edge.BoundBox.ZMin >= FRONT_HEIGHT - 1e-6]
    shell = shell.makeFillet(0.65, rim).removeSplitter()
    notches = [
        cable_slot(lambda x, z: V(x, DEPTH - FRONT - 1, z),
                   center, 7, 65, V(0, FRONT + 2, 0), height=HEIGHT)
        for center in CENTERS
    ]
    with_slots = shell.cut(notches)
    return with_slots.fuse([partition(x) for x in (-PITCH / 2, PITCH / 2)]).removeSplitter()


def check(shape):
    assert shape.isValid() and shape.isClosed() and len(shape.Solids) == 1
    box = shape.optimalBoundingBox(False, False)
    for length, expected in zip((box.XLength, box.YLength, box.ZLength), (WIDTH, DEPTH, HEIGHT)):
        near(length, expected)

    for x in CENTERS:
        width, depth, height = FIT
        base = V(x - width / 2, (BACK + DEPTH - FRONT - depth) / 2, FLOOR)
        # A full rectangular envelope can enter vertically from above.
        probe = Part.makeBox(width, depth, height + HEIGHT, base)
        assert shape.common(probe).Volume < 1e-6
        front_y = DEPTH - FRONT / 2
        assert shape.isInside(V(x, front_y, 57.9), 1e-6, False)
        assert not shape.isInside(V(x, front_y, 58.1), 1e-6, False)
        assert not shape.isInside(V(x + 6.9, front_y, 69), 1e-6, False)
        assert shape.isInside(V(x + 7.1, front_y, 69), 1e-6, False)

    for x in (-PITCH / 2, PITCH / 2):
        assert shape.isInside(V(x, 30, 65), 1e-6, False)

    for x in TAPE_CENTERS:
        left, right = x - TAPE_WIDTH / 2, x + TAPE_WIDTH / 2
        bottom, top = TAPE_Z, TAPE_Z + TAPE_HEIGHT
        patch = Part.Face(wire_from_points([
            V(left, 0, bottom), V(right, 0, bottom), V(right, 0, top), V(left, 0, top),
        ]))
        near(patch.common(shape).Area, TAPE_WIDTH * TAPE_HEIGHT)


def capacity():
    width, height = LOOP
    per_turn = math.pi * width + 2 * (height - width)
    cases = []
    for length, diameter in CABLE_CASES:
        turns = math.ceil(length * 1000 / per_turn)
        coil = (width + diameter, turns * diameter + 4, height + diameter)
        assert all(measured <= limit for measured, limit in zip(coil, FIT))
        cases.append(dict(length_m=length, diameter_mm=diameter, turns=turns,
                          envelope_with_tie_mm=coil))
    return cases


def main():
    shape = build()
    check(shape)
    native = ROOT / "cad" / f"{NAME}.FCStd"
    step_path = ROOT / "cad" / f"{NAME}.step"
    stl = ROOT / "printing" / f"{NAME}.stl"
    doc = App.newDocument("BedsideCableTray")
    body = doc.addObject("Part::Feature", "CableTray")
    body.Label = "V2 · 三格长线仓"
    body.Shape = shape
    doc.recompute()
    doc.saveAs(str(native))
    shape.exportStep(str(step_path))
    mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.06,
                                 AngularDeflection=0.10, Relative=False)
    mesh.write(str(stl))

    App.closeDocument(doc.Name)
    saved = App.openDocument(str(native)).getObject("CableTray").Shape
    check(saved)
    step = Part.Shape()
    step.read(str(step_path))
    check(step)
    near(step.Volume, saved.Volume, 0.01)
    exported = Mesh.Mesh(str(stl))
    assert exported.isSolid() and exported.countComponents() == 1
    near(exported.Volume, saved.Volume, saved.Volume * 0.002)
    print(json.dumps({
        "exterior_mm": [WIDTH, DEPTH, HEIGHT],
        "pocket_straight_width_mm": round(POCKET, 2),
        "vertical_insertion_envelope_mm": FIT,
        "coil_centerline_mm": LOOP,
        "case_per_pocket": capacity(),
        "stl_triangles": exported.CountFacets,
    }, indent=2))


if __name__ == "__main__":
    main()
