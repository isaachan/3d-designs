"""Add integral under-box braces to the V3 sketch box."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
from v3 import build as v3
from build import App, Mesh, MeshPart, Part, V, near, wire_from_points

NAME = "bedside-braced-box"
DROP = 45
REACH = 90
HEEL = 8
RIB_THICKNESS = 6
RIB_CENTERS = (-47, 47)
UPPER_TAPE_BOTTOM = 16
LOWER_TAPE_BOTTOM = -40
LOWER_TAPE_HEIGHT = 35
FLAT_BACK_WIDTH = v3.WIDTH - 6


def rib(center):
    x = center - RIB_THICKNESS / 2
    outline = wire_from_points([
        V(x, v3.BACK - 1, -DROP),
        V(x, HEEL, -DROP),
        V(x, REACH, 0),
        V(x, REACH, 1),
        V(x, v3.BACK - 1, 1),
    ])
    return Part.Face(outline).extrude(V(RIB_THICKNESS, 0, 0))


def build(original):
    extension = Part.makeBox(FLAT_BACK_WIDTH, v3.BACK, DROP + 1,
                             V(-FLAT_BACK_WIDTH / 2, 0, -DROP))
    return original.fuse([extension, *(rib(x) for x in RIB_CENTERS)]).removeSplitter()


def check(shape, original):
    assert shape.isValid() and shape.isClosed() and len(shape.Solids) == 1
    bounds = shape.optimalBoundingBox(False, False)
    for measured, expected in zip(
        (bounds.XLength, bounds.YLength, bounds.ZMin, bounds.ZMax),
        (v3.WIDTH, v3.DEPTH, -DROP, v3.REAR_HEIGHT),
    ):
        near(measured, expected)

    # All changes are outside and below the original storage volume.
    upper = Part.makeBox(v3.WIDTH + 2, v3.DEPTH + 2, v3.REAR_HEIGHT + 1,
                         V(-v3.WIDTH / 2 - 1, -1, 0))
    near(shape.common(upper).Volume, original.Volume)
    near(shape.common(original).Volume, original.Volume)
    for x in RIB_CENTERS:
        mid_y = (HEEL + REACH) / 2
        assert shape.isInside(V(x, mid_y, -DROP / 2 + 0.1), 1e-6, False)
        assert not shape.isInside(V(x, mid_y, -DROP / 2 - 0.1), 1e-6, False)
        for bottom, height in ((UPPER_TAPE_BOTTOM, v3.TAPE_HEIGHT),
                               (LOWER_TAPE_BOTTOM, LOWER_TAPE_HEIGHT)):
            left = x - v3.TAPE_WIDTH / 2
            right = x + v3.TAPE_WIDTH / 2
            top = bottom + height
            patch = Part.Face(wire_from_points([
                V(left, 0, bottom), V(right, 0, bottom),
                V(right, 0, top), V(left, 0, top),
            ]))
            near(patch.common(shape).Area, v3.TAPE_WIDTH * height)


def main():
    original = v3.build()
    shape = build(original)
    check(shape, original)

    native = ROOT / "cad" / f"{NAME}.FCStd"
    step_path = ROOT / "cad" / f"{NAME}.step"
    stl = ROOT / "printing" / f"{NAME}.stl"
    doc = App.newDocument("BedsideBracedBox")
    body = doc.addObject("Part::Feature", "BracedBox")
    body.Label = "床头斜口盒 · 一体三角撑"
    body.Shape = shape
    doc.recompute()
    doc.saveAs(str(native))
    shape.exportStep(str(step_path))

    # Upright on the lower extension, ready to slice with external supports.
    printable = shape.copy()
    printable.translate(V(0, 0, DROP))
    mesh = MeshPart.meshFromShape(Shape=printable, LinearDeflection=0.06,
                                 AngularDeflection=0.10, Relative=False)
    mesh.write(str(stl))

    App.closeDocument(doc.Name)
    reopened = App.openDocument(str(native))
    check(reopened.getObject("BracedBox").Shape, original)
    step = Part.Shape()
    step.read(str(step_path))
    check(step, original)
    near(step.Volume, shape.Volume, 0.01)
    exported = Mesh.Mesh(str(stl))
    assert exported.isSolid() and exported.countComponents() == 1
    near(exported.BoundBox.ZMin, 0)
    near(exported.Volume, shape.Volume, shape.Volume * 0.002)
    print("Verified V3 cavity, both triangular braces and coplanar upper/lower tape pads.")
    print(f"150 × 100 × {v3.REAR_HEIGHT + DROP} mm, {exported.CountFacets} STL facets.")


if __name__ == "__main__":
    main()
