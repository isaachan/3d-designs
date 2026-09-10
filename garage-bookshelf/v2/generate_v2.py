"""Generate the v2 modular bookshelf STL package with FreeCAD/OpenCascade.

Run with:
  /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd generate_v2.py
"""
from pathlib import Path
import json
import subprocess
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


def tapered_prism(root, tip):
    """Make a solid between matching four-point sections at its X ends."""
    # OpenCascade's loft makes the four non-planar-looking side faces robustly
    # and avoids hand-orienting a shell for every taper direction.
    root_wire = Part.makePolygon(root + [root[0]])
    tip_wire = Part.makePolygon(tip + [tip[0]])
    return Part.makeLoft([root_wire, tip_wire], True, False).removeSplitter()


def dovetail_base(x, center, depth, clearance=0):
    """Sliding dovetail, visibly tail-shaped in plan and locking in elevation."""
    z0, z1 = -0.2 if clearance else 0, BASE_H + (0.2 if clearance else 0)
    # The root is deliberately wider than the tip in both plan and elevation.
    root_bottom, root_top = 15 + clearance, 12 + clearance
    tip_bottom, tip_top = 12 + clearance, 9 + clearance
    root = [App.Vector(x, center - root_bottom, z0), App.Vector(x, center + root_bottom, z0),
            App.Vector(x, center + root_top, z1), App.Vector(x, center - root_top, z1)]
    end = x + depth
    tip = [App.Vector(end, center - tip_bottom, z0), App.Vector(end, center + tip_bottom, z0),
           App.Vector(end, center + tip_top, z1), App.Vector(end, center - tip_top, z1)]
    return tapered_prism(root, tip)


def dovetail_back(x, center_z, depth, clearance=0):
    """Sliding dovetail, visibly tail-shaped when viewed along the back."""
    front_y, rear_y = 214.8 - clearance, 220 + clearance
    root_front_h, root_rear_h = 13 + clearance, 17 + clearance
    tip_front_h, tip_rear_h = 10 + clearance, 14 + clearance
    root = [App.Vector(x, front_y, center_z - root_front_h), App.Vector(x, front_y, center_z + root_front_h),
            App.Vector(x, rear_y, center_z + root_rear_h), App.Vector(x, rear_y, center_z - root_rear_h)]
    end = x + depth
    tip = [App.Vector(end, front_y, center_z - tip_front_h), App.Vector(end, front_y, center_z + tip_front_h),
           App.Vector(end, rear_y, center_z + tip_rear_h), App.Vector(end, rear_y, center_z - tip_rear_h)]
    return tapered_prism(root, tip)


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
    # Two printable 180 mm halves replace an unprintable 360 mm deck.  The
    # inside edge has two full-thickness X-sliding dovetails; a separate
    # underside bridge carries the seam in bending after it is glued.
    x0 = 180 if right else 0
    profile = [(0,0),(153,0),(153,17),(167,17),(167,0),(180,0),(180,215),(167,215),(167,188),(153,188),(153,215),(0,215)]
    wire = Part.makePolygon([App.Vector(x0 + x, y, z) for x,y in profile] + [App.Vector(x0,0,z)])
    shape = Part.Face(wire).extrude(App.Vector(0,0,5))
    for y in (55, 160):
        if right:
            shape = shape.cut(deck_dovetail(179.8, y, 10.2, z, CLEARANCE / 2))
        else:
            shape = shape.fuse(deck_dovetail(179.8, y, 10, z))
    return clean(shape)


def deck_dovetail(x, center_y, depth, z, clearance=0):
    """5 mm deck dovetail: root 22/16 mm, tip 16/12 mm, both axes tapered."""
    z0, z1 = z - (.2 if clearance else 0), z + 5 + (.2 if clearance else 0)
    root_bottom, root_top = 11 + clearance, 8 + clearance
    tip_bottom, tip_top = 8 + clearance, 6 + clearance
    root = [App.Vector(x, center_y - root_bottom, z0), App.Vector(x, center_y + root_bottom, z0),
            App.Vector(x, center_y + root_top, z1), App.Vector(x, center_y - root_top, z1)]
    end = x + depth
    tip = [App.Vector(end, center_y - tip_bottom, z0), App.Vector(end, center_y + tip_bottom, z0),
           App.Vector(end, center_y + tip_top, z1), App.Vector(end, center_y - tip_top, z1)]
    return tapered_prism(root, tip)


def deck_seam_bridge(z):
    """A glued 48 x 110 x 3 mm underside doubler across the deck seam."""
    return Part.makeBox(48, 110, 3, App.Vector(156, 55, z - 3))


def column():
    # v2 has no overhead header; columns stop at Z=230 below body top Z=238.
    body = Part.makeCylinder(6, 222, App.Vector(10,10,8))
    for z in (54, 117, 180):
        body = body.fuse(Part.makeCone(6, 14, 8, App.Vector(10,10,8 + z - 8)))
        body = body.fuse(Part.makeCylinder(14, 4, App.Vector(10,10,8 + z)))
    return clean(body)


def panel_shape(width, height, thickness):
    return Part.makeBox(width, height, thickness)


def billboard_text_shape(text, width, font_size, x0, z0):
    """White PLA text, made from the v2-owned AppKit mask generator.

    Text is printed as a separate cosmetic STL.  Letter islands are expected;
    each island is a closed manifold, and all are glued to the black board.
    """
    mask = json.loads(subprocess.check_output([
        "/usr/bin/swift", str(ROOT / "generate-label-mask.swift"), text,
        str(font_size), str(width), "28", "horizontal",
    ], text=True))
    # Slight overlap turns both edge- and corner-adjacent raster pixels into
    # real volume intersections before the Boolean union.  Mere edge contact
    # would make a non-manifold letter in an STL.
    boxes = [Part.makeBox(run + .10, 1, 1.10, App.Vector(x0 + x - .05, 219, z0 + y - .05)) for x, y, run in mask]
    # Fuse adjacent raster runs before STL export so coincident faces cannot
    # turn a letter island non-manifold.
    return boxes[0].multiFuse(boxes[1:]).removeSplitter()


def export(name, shape, multi_solid=False):
    if not shape.isValid() or (not multi_solid and len(shape.Solids) != 1):
        raise RuntimeError(f"{name} is not one valid solid")
    if multi_solid and (not shape.Solids or not all(s.isValid() for s in shape.Solids)):
        raise RuntimeError(f"{name} has invalid text islands")
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
    export(f"garage_deck_{level}_left", deck_half("", False, z))
    export(f"garage_deck_{level}_right", deck_half("", True, z))
    export(f"garage_deck_{level}_seam_bridge", clean(deck_seam_bridge(z)))
for index in range(1,5): export(f"garage_column_{index}", column())
export("book_depot_sign", panel_shape(36,180,6))

# The billboard is deliberately independent of the 238 mm structural envelope.
# Two equal 24 mm-wide posts have centres X=90 and X=270, symmetric about its
# X=180 centreline.  The assembly is lowered 30 mm from the prior position;
# posts Z=150..300 retain an 88 mm glue land on the rear back panel.
export("billboard_left", Part.makeBox(180, 6, 64, App.Vector(0, 220, 300)))
export("billboard_right", Part.makeBox(180, 6, 64, App.Vector(180, 220, 300)))
export("billboard_seam_bridge", Part.makeBox(50, 3, 36, App.Vector(155, 226, 314)))
export("billboard_post_left", Part.makeBox(24, 6, 150, App.Vector(78, 220, 150)))
export("billboard_post_right", Part.makeBox(24, 6, 150, App.Vector(258, 220, 150)))
# Two short lines keep every white text part inside the X2D bed.
export("billboard_text_lovely_cars", billboard_text_shape("Lovely Cars", 180, 26, 90, 332), multi_solid=True)
export("billboard_text_ive_driven", billboard_text_shape("I've Driven", 180, 26, 90, 304), multi_solid=True)
test_shapes()
print(f"Generated {len(list(OUT.glob('*.stl')))} v2 STL files in {OUT}")
