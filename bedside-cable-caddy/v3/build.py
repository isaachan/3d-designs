"""Build the open, sloped-top box from the hand sketch."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
from build import App, Mesh, MeshPart, Part, V, near, rounded_plan, wire_from_points

NAME = "bedside-slope-box"
WIDTH = 150
DEPTH = 100
REAR_HEIGHT = 120
FRONT_HEIGHT = 80
BACK = 4
WALL = 3
FLOOR = 3.4
TAPE_WIDTH = 25
TAPE_HEIGHT = 85
TAPE_BOTTOM = 16
TAPE_CENTERS = (-47, 47)


def top_at(y):
    return REAR_HEIGHT + y * (FRONT_HEIGHT - REAR_HEIGHT) / DEPTH


def build():
    left = -WIDTH / 2
    profile = Part.Face(wire_from_points([
        V(left - 1, -1, -1),
        V(left - 1, DEPTH + 1, -1),
        V(left - 1, DEPTH + 1, top_at(DEPTH + 1)),
        V(left - 1, -1, top_at(-1)),
    ]))
    envelope = profile.extrude(V(WIDTH + 2, 0, 0))
    outside = rounded_plan(left, 0, -left, DEPTH, 3, 0).extrude(V(0, 0, REAR_HEIGHT + 1))
    inside = rounded_plan(left + WALL, BACK, -left - WALL, DEPTH - WALL, 2, FLOOR)
    cavity = inside.extrude(V(0, 0, REAR_HEIGHT))
    return outside.common(envelope).cut(cavity).removeSplitter()


def check(shape):
    assert shape.isValid() and shape.isClosed() and len(shape.Solids) == 1
    bounds = shape.optimalBoundingBox(False, False)
    for measured, expected in zip(
        (bounds.XLength, bounds.YLength, bounds.ZLength, bounds.ZMin),
        (WIDTH, DEPTH, REAR_HEIGHT, 0),
    ):
        near(measured, expected)

    for y in (0, 25, 50, 75, DEPTH):
        # The same uninterrupted slope runs along both end walls.
        x = WIDTH / 2 - 1
        if y in (0, DEPTH):
            x -= 3
        top = V(x, y, top_at(y))
        assert shape.isInside(top, 1e-6, True)
        assert not shape.isInside(top + V(0, 0, 0.01), 1e-6, True)

    # Verify a large rectangular footprint can drop in vertically from above.
    opening = Part.makeBox(140, 89, REAR_HEIGHT, V(-70, 6, FLOOR))
    near(shape.common(opening).Volume, 0)
    assert shape.isInside(V(0, DEPTH / 2, FLOOR / 2), 1e-6, False)

    for x in TAPE_CENTERS:
        left, right = x - TAPE_WIDTH / 2, x + TAPE_WIDTH / 2
        bottom, top = TAPE_BOTTOM, TAPE_BOTTOM + TAPE_HEIGHT
        patch = Part.Face(wire_from_points([
            V(left, 0, bottom), V(right, 0, bottom), V(right, 0, top), V(left, 0, top),
        ]))
        near(patch.common(shape).Area, TAPE_WIDTH * TAPE_HEIGHT)


def main():
    shape = build()
    check(shape)
    native = ROOT / "cad" / f"{NAME}.FCStd"
    step_path = ROOT / "cad" / f"{NAME}.step"
    stl = ROOT / "printing" / f"{NAME}.stl"
    doc = App.newDocument("BedsideSlopeBox")
    body = doc.addObject("Part::Feature", "SlopeBox")
    body.Label = "床头斜口盒"
    body.Shape = shape
    doc.recompute()
    doc.saveAs(str(native))
    shape.exportStep(str(step_path))
    mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.06,
                                 AngularDeflection=0.10, Relative=False)
    mesh.write(str(stl))

    App.closeDocument(doc.Name)
    reopened = App.openDocument(str(native))
    check(reopened.getObject("SlopeBox").Shape)
    step = Part.Shape()
    step.read(str(step_path))
    check(step)
    near(step.Volume, shape.Volume, 0.01)
    exported = Mesh.Mesh(str(stl))
    assert exported.isSolid() and exported.countComponents() == 1
    near(exported.Volume, shape.Volume, shape.Volume * 0.002)
    print(f"Verified 150 × 100 mm, rear 120 mm, front 80 mm; {exported.CountFacets} STL facets.")


if __name__ == "__main__":
    main()
