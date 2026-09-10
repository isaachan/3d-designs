"""Generate the v2 modular bookshelf STL package with FreeCAD/OpenCascade.

Run with:
  /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd generate_v2.py
"""
from pathlib import Path
import FreeCAD as App
import Part
import Mesh

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "stl"
OUT.mkdir(exist_ok=True)

# Millimetres.  A single source of truth for the printable interfaces.
CUTS = (0, 180, 410, 590, 770, 920)
DEPTH, BASE_H, BACK_T, WALL_T, BODY_H = 220, 8, 5, 6, 238
WALL_H = BODY_H - BASE_H
TONGUE = 14.0
SOCKET_DEPTH = 15.0
CLEARANCE = 0.40
BRIM = 4.0


def dovetail_base(x, center, depth, clearance=0):
    """A sliding dovetail with a constant YZ profile, extruded along X."""
    bottom, top = 15 + clearance, 12 + clearance
    points = [
        App.Vector(x, center - bottom, -0.2 if clearance else 0),
        App.Vector(x, center + bottom, -0.2 if clearance else 0),
        App.Vector(x, center + top, BASE_H + (0.2 if clearance else 0)),
        App.Vector(x, center - top, BASE_H + (0.2 if clearance else 0)),
    ]
    return Part.Face(Part.makePolygon(points + [points[0]])).extrude(App.Vector(depth, 0, 0))


def dovetail_back(x, center_z, depth, clearance=0):
    """A sliding dovetail with a constant YZ profile, extruded along X."""
    front_y, rear_y = 214.8 - clearance, 220 + clearance
    front_h, rear_h = 13 + clearance, 17 + clearance
    points = [
        App.Vector(x, front_y, center_z - front_h),
        App.Vector(x, front_y, center_z + front_h),
        App.Vector(x, rear_y, center_z + rear_h),
        App.Vector(x, rear_y, center_z - rear_h),
    ]
    return Part.Face(Part.makePolygon(points + [points[0]])).extrude(App.Vector(depth, 0, 0))


def rib(x, y, inward):
    """25 x 25 x 5 root gusset, overlapping the panel/base for a true union."""
    points = [App.Vector(x, y, 7.8), App.Vector(x + inward * 25, y, 7.8), App.Vector(x, y, 32.8)]
    return Part.Face(Part.makePolygon(points + [points[0]])).extrude(App.Vector(0, 5, 0))


def clean(shape):
    result = shape.removeSplitter()
    if not result.isValid() or len(result.Solids) != 1:
        raise RuntimeError(f"Expected one valid solid, got valid={result.isValid()} solids={len(result.Solids)}")
    return result


def make_module(index, x0, x1):
    # Base and back overlap by 0.2 mm at Z=8, forming a single load path.
    shape = Part.makeBox(x1 - x0, DEPTH, BASE_H, App.Vector(x0, 0, 0))
    shape = shape.fuse(Part.makeBox(x1 - x0, BACK_T, WALL_H + 0.2, App.Vector(x0, DEPTH - BACK_T, 7.8)))

    # Keep the specified panels and their integral front/rear gussets wholly
    # inside their designated modules.
    if index == 2:
        panel = Part.makeBox(WALL_T, 215, WALL_H + 0.2, App.Vector(360, 0, 7.8))
        shape = shape.fuse(panel).fuse(rib(365.8, 12, 1)).fuse(rib(365.8, 183, 1))
    if index == 5:
        panel = Part.makeBox(WALL_T, 215, WALL_H + 0.2, App.Vector(914, 0, 7.8))
        shape = shape.fuse(panel).fuse(rib(914.2, 12, -1)).fuse(rib(914.2, 183, -1))

    # Every joint uses the same X insertion axis.  A left module carries male
    # tongues toward +X; the next module receives them in +X-facing sockets.
    if index < 5:
        for y in (52, 168):
            shape = shape.fuse(dovetail_base(x1 - 0.2, y, TONGUE))
        for z in (66, 180):
            shape = shape.fuse(dovetail_back(x1 - 0.2, z, TONGUE))
    if index > 1:
        for y in (52, 168):
            shape = shape.cut(dovetail_base(x0 - 0.2, y, SOCKET_DEPTH, CLEARANCE / 2))
        for z in (66, 180):
            shape = shape.cut(dovetail_back(x0 - 0.2, z, SOCKET_DEPTH, CLEARANCE / 2))
    return clean(shape)


def deck_half(name, right, z):
    # Same 180 x 215 half-deck layout and column clearances as v1.
    x0 = 180 if right else 0
    profile = [(0,0),(153,0),(153,17),(167,17),(167,0),(180,0),(180,215),(167,215),(167,188),(153,188),(153,215),(0,215)]
    wire = Part.makePolygon([App.Vector(x0 + x, y, z) for x,y in profile] + [App.Vector(x0,0,z)])
    return Part.Face(wire).extrude(App.Vector(0,0,5))


def column():
    # v2 has no overhead header; columns stop at Z=230 below body top Z=238.
    body = Part.makeCylinder(6, 222, App.Vector(10,10,8))
    for z in (54, 117, 180):
        body = body.fuse(Part.makeCone(6, 14, 8, App.Vector(10,10,8 + z - 8)))
        body = body.fuse(Part.makeCylinder(14, 4, App.Vector(10,10,8 + z)))
    return clean(body)


def panel_shape(width, height, thickness):
    return Part.makeBox(width, height, thickness)


def export(name, shape):
    if not shape.isValid() or len(shape.Solids) != 1:
        raise RuntimeError(f"{name} is not one valid solid")
    shape.exportStl(str(OUT / f"{name}.stl"))


def test_shapes():
    # Separate base/back fit pairs, plus one complete four-dovetail corner pair.
    base_male = Part.makeBox(70, 100, BASE_H).fuse(dovetail_base(69.8, 50, TONGUE))
    base_female = Part.makeBox(70, 100, BASE_H, App.Vector(0, 0, 0)).cut(dovetail_base(-0.2, 50, SOCKET_DEPTH, CLEARANCE / 2))
    back_male = Part.makeBox(70, BACK_T, 80, App.Vector(0, DEPTH-BACK_T, 8)).fuse(dovetail_back(69.8, 48, TONGUE))
    back_female = Part.makeBox(70, BACK_T, 80, App.Vector(0, DEPTH-BACK_T, 8)).cut(dovetail_back(-0.2, 48, SOCKET_DEPTH, CLEARANCE / 2))
    export("test_base_male", clean(base_male)); export("test_base_female", clean(base_female))
    export("test_back_male", clean(back_male)); export("test_back_female", clean(back_female))

    def corner(left):
        x0, x1 = (0, 70) if left else (70, 140)
        s = Part.makeBox(70, DEPTH, BASE_H, App.Vector(x0,0,0)).fuse(Part.makeBox(70,BACK_T,WALL_H+.2,App.Vector(x0,DEPTH-BACK_T,7.8)))
        if left:
            for y in (52,168): s=s.fuse(dovetail_base(69.8,y,TONGUE))
            for z in (66,180): s=s.fuse(dovetail_back(69.8,z,TONGUE))
        else:
            for y in (52,168): s=s.cut(dovetail_base(69.8,y,SOCKET_DEPTH,CLEARANCE/2))
            for z in (66,180): s=s.cut(dovetail_back(69.8,z,SOCKET_DEPTH,CLEARANCE/2))
        return clean(s)
    export("test_corner_left_four_male", corner(True)); export("test_corner_right_four_female", corner(False))


for i, (x0, x1) in enumerate(zip(CUTS, CUTS[1:]), 1):
    export(f"module_{i}", make_module(i, x0, x1))

# Retained garage display: 3 decks, 4 support columns, no former top header or billboard.
for level, z in enumerate((66, 129, 192), 1):
    export(f"garage_deck_{level}_left", clean(deck_half("", False, z)))
    export(f"garage_deck_{level}_right", clean(deck_half("", True, z)))
for index in range(1,5): export(f"garage_column_{index}", column())
export("book_depot_sign", panel_shape(36,180,6))

# Text is deliberately omitted from v2 printable structural package until it is
# regenerated from the label source in a dedicated cosmetic pass.
test_shapes()
print(f"Generated {len(list(OUT.glob('*.stl')))} v2 STL files in {OUT}")
