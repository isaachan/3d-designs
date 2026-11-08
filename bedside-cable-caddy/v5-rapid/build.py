"""Build the support-free box and two wall braces for the rapid print plate."""

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from build import App, Mesh, MeshPart, Part, V, near, rounded_plan, wire_from_points
from v3 import build as v3

NAME = "bedside-rapid-box"
WALL = 0.60
FLOOR = 1.12
WIDTH, DEPTH = v3.WIDTH, v3.DEPTH
BRACE_WIDTH = 10
BRACE_DROP = 45
BRACE_REACH = 84
BRACE_CENTERS = (-47, 47)
PLATE_OFFSETS = (V(-85, 108, 0), V(9, 108, 0))


def trough():
    left = -WIDTH / 2
    section = Part.Face(wire_from_points([
        V(left - 1, -1, -1), V(left - 1, DEPTH + 1, -1),
        V(left - 1, DEPTH + 1, v3.top_at(DEPTH + 1)),
        V(left - 1, -1, v3.top_at(-1)),
    ])).extrude(V(WIDTH + 2, 0, 0))
    outer = rounded_plan(left, 0, -left, DEPTH, 3, 0).extrude(V(0, 0, 121))
    inner = rounded_plan(left + WALL, WALL, -left - WALL, DEPTH - WALL, 3 - WALL, FLOOR)
    shell = outer.common(section).cut(inner.extrude(V(0, 0, 121)))
    pads = [Part.makeBox(26, 1.6, 105, V(x - 13, 0.4, FLOOR - 0.2)) for x in BRACE_CENTERS]
    ribs = []
    for y in (13, 30, 47, 64, 81, 94):
        x = -74.5
        outline = wire_from_points([
            V(x, y - 2.1, FLOOR - 0.12), V(x, y + 2.1, FLOOR - 0.12),
            V(x, y + 0.45, FLOOR + 2.6), V(x, y - 0.45, FLOOR + 2.6),
        ])
        ribs.append(Part.Face(outline).extrude(V(149, 0, 0)))
    return shell.fuse(pads + ribs).removeSplitter()


def flat_brace():
    outline = Part.Face(wire_from_points([
        V(0, 0, 0), V(BRACE_REACH, 0, 0), V(5, BRACE_DROP, 0), V(0, BRACE_DROP, 0),
    ])).extrude(V(0, 0, BRACE_WIDTH))
    window = Part.Face(wire_from_points([
        V(2.8, 2.8, -1), V(73, 2.8, -1), V(5.6, 40.6, -1), V(2.8, 40.6, -1),
    ])).extrude(V(0, 0, BRACE_WIDTH + 2))
    return outline.cut(window).removeSplitter()


def mounted_brace(part, x):
    matrix = App.Matrix()
    matrix.A11, matrix.A12, matrix.A13, matrix.A14 = 0, 0, -1, x + BRACE_WIDTH / 2
    matrix.A21, matrix.A22, matrix.A23 = 1, 0, 0
    matrix.A31, matrix.A32, matrix.A33 = 0, -1, 0
    result = part.copy()
    result.transformShape(matrix)
    return result


def check(box, supports):
    for shape in (box, *supports):
        assert shape.isValid() and shape.isClosed() and len(shape.Solids) == 1
    bounds = box.optimalBoundingBox(False, False)
    for length, expected in zip((bounds.XLength, bounds.YLength, bounds.ZLength), (150, 100, 120)):
        near(length, expected)

    for center, support in zip(BRACE_CENTERS, supports):
        for body, width, low, high in ((box, 25, 16, 101), (support, 10, -40, -5)):
            left, right = center - width / 2, center + width / 2
            adhesive = Part.Face(wire_from_points([
                V(left, 0, low), V(right, 0, low), V(right, 0, high), V(left, 0, high),
            ]))
            near(adhesive.common(body).Area, width * (high - low))
        # Brace ledges meet the outside floor on both sides with no interference.
        contact = Part.Face(wire_from_points([
            V(center - 5, 0, 0), V(center + 5, 0, 0),
            V(center + 5, BRACE_REACH, 0), V(center - 5, BRACE_REACH, 0),
        ]))
        near(contact.common(box).Area, BRACE_WIDTH * BRACE_REACH)
        near(contact.common(support).Area, BRACE_WIDTH * BRACE_REACH)
        near(box.common(support).Volume, 0)


def main():
    box, brace = trough(), flat_brace()
    mounted = [mounted_brace(brace, x) for x in BRACE_CENTERS]
    check(box, mounted)
    doc = App.newDocument("BedsideRapidBox")
    for name, label, shape in zip(("Box", "LeftBrace", "RightBrace"),
                                  ("斜口盒", "左斜撑", "右斜撑"), (box, *mounted)):
        item = doc.addObject("Part::Feature", name)
        item.Label = label
        item.Shape = shape
    doc.recompute()
    doc.saveAs(str(HERE / "cad" / f"{NAME}.FCStd"))
    Part.makeCompound([box, *mounted]).exportStep(str(HERE / "cad" / f"{NAME}.step"))

    print_braces = [brace.copy() for _ in PLATE_OFFSETS]
    for part, offset in zip(print_braces, PLATE_OFFSETS):
        part.translate(offset)
    plate = Part.makeCompound([box, *print_braces])
    mesh = MeshPart.meshFromShape(Shape=plate, LinearDeflection=0.04, AngularDeflection=0.1, Relative=False)
    stl = HERE / "printing" / f"{NAME}.stl"
    mesh.write(str(stl))
    exported = Mesh.Mesh(str(stl))
    assert exported.isSolid() and exported.countComponents() == 3
    near(exported.BoundBox.ZMin, 0)
    print("Verified 3 closed parts, 4 flat tape zones, and both flush brace-to-floor contacts.")


if __name__ == "__main__":
    main()
