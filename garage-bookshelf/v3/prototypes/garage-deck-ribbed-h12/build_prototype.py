"""Build one printable garage deck load-test specimen with 12 mm underside ribs.

This is a separate prototype. The committed v3 assembly is never opened for writing.
Run with the Python bundled in FreeCAD, not system Python.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
V3 = ROOT.parents[1]
sys.path.insert(0, "/Applications/FreeCAD.app/Contents/Resources/lib")
sys.path.insert(0, str(V3))

import FreeCAD as App
import Mesh
import MeshPart
import Part
import parameters
from assembly import bodies, global_shape, group, part, parts
from components import shelves
from geometry.features import finish, pad, pocket
from geometry.sketches import circle, loops, rectangle


PROTOTYPE_PARAMETERS = [
    ("DeckRibHeight", "12 mm", "梁自层板底面向下的高度 h"),
    ("DeckRibWidth", "12 mm", "前后梁在板底的宽度"),
    ("DeckRibFrontY", "22 mm", "前梁起始 Y，避开前端开口"),
    ("DeckRibRearY", "172 mm", "后梁起始 Y，避开后端开口及中央跨缝片"),
    ("DeckRibSupportMargin", "1 mm", "梁端与测试支座接触圆的最小平面间隔"),
    ("DeckRibLeftStart", "=ColumnCentreOffset+CollarRadius+DeckRibSupportMargin", "左半片梁起点"),
    ("DeckRibRightEnd", "=ColumnPitchX+ColumnCentreOffset-DeckHalfWidth-CollarRadius-DeckRibSupportMargin", "右半片梁终点"),
    ("DeckSpliceLap", "35 mm", "跨缝条在每半片梁上的名义搭接长度"),
    ("DeckSpliceLength", "=2*DeckSpliceLap", "跨缝条总长度"),
    ("DeckSpliceThickness", "3 mm", "跨缝条厚度"),
    ("DeckSpliceGlueGap", "0.2 mm", "跨缝条槽侧面和深度的胶层空间"),
    ("DeckSpliceGrooveWidth", "=DeckRibWidth+2*DeckSpliceGlueGap", "梁底胶接凹槽宽度"),
    ("DeckSpliceGrooveDepth", "=DeckSpliceThickness+DeckSpliceGlueGap", "梁底胶接凹槽深度"),
    ("DeckSpliceX", "=DeckHalfWidth-DeckSpliceLap", "跨缝条全局 X"),
    ("DeckFixtureHeight", "20 mm", "台架试验的独立支座高度"),
]


def register_parameters():
    known = {item[0] for item in parameters.PARAMETERS}
    for item in PROTOTYPE_PARAMETERS:
        if item[0] not in known:
            parameters.PARAMETERS.append(item)


def reversed_pad(body, name, sketch, length):
    feature = body.newObject("PartDesign::Pad", name)
    feature.Profile = sketch
    feature.setExpression("Length", parameters.expression(length))
    feature.Reversed = True
    feature.Refine = True
    return finish(body, feature)


def reversed_pocket(body, name, sketch, length):
    feature = body.newObject("PartDesign::Pocket", name)
    feature.Profile = sketch
    feature.setExpression("Length", parameters.expression(length))
    feature.Reversed = True
    feature.Refine = True
    return finish(body, feature)


def rib_polygons(right):
    x0 = "Zero" if right else "DeckRibLeftStart"
    x1 = "DeckRibRightEnd" if right else "DeckHalfWidth"
    result = []
    for y0 in ("DeckRibFrontY", "DeckRibRearY"):
        y1 = f"{y0}+DeckRibWidth"
        result.append([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    return result


def groove_polygons(right):
    x0 = "Zero" if right else "DeckHalfWidth-DeckSpliceLap"
    x1 = "DeckSpliceLap" if right else "DeckHalfWidth"
    result = []
    for y in ("DeckRibFrontY", "DeckRibRearY"):
        y0 = f"{y}-DeckSpliceGlueGap"
        y1 = f"{y0}+DeckSpliceGrooveWidth"
        result.append([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    return result


def deck(body, right):
    shelves.build(body, right)
    ribs = loops(body, "Sketch_UndersideRibs", rib_polygons(right))
    reversed_pad(body, "Pad_UndersideRibs", ribs, "DeckRibHeight")
    seats = loops(body, "Sketch_SpliceSeats", groove_polygons(right),
                  offset=("Zero", "Zero", "-DeckRibHeight"))
    reversed_pocket(body, "Pocket_SpliceSeats", seats, "DeckSpliceGrooveDepth")


def build():
    register_parameters()
    if "GarageDeckRibbedH12" in App.listDocuments():
        App.closeDocument("GarageDeckRibbedH12")
    doc = App.newDocument("GarageDeckRibbedH12")
    parameters.create(doc)
    deck_group = group(doc, "ReinforcedDeck", "01 单层加固层板")
    _, left = part(doc, deck_group, "reinforced_deck_left", "加固层板左半片")
    deck(left, False)
    _, right = part(doc, deck_group, "reinforced_deck_right", "加固层板右半片",
                    ("DeckHalfWidth", "Zero", "Zero"))
    deck(right, True)

    joint_group = group(doc, "Splices", "02 中缝连接件")
    _, bridge = part(doc, joint_group, "original_centre_bridge", "原中央跨缝片",
                     ("DeckBridgeX", "DeckBridgeY", "-DeckBridgeThickness"))
    pad(bridge, "Pad_CentreBridge", rectangle(bridge, "Sketch_CentreBridge",
        "DeckBridgeWidth", "DeckBridgeDepth"), "DeckBridgeThickness")
    for name, y, label in (
        ("front_splice", "DeckRibFrontY", "前梁跨缝条"),
        ("rear_splice", "DeckRibRearY", "后梁跨缝条"),
    ):
        _, body = part(doc, joint_group, name, label,
                       ("DeckSpliceX", y, "-DeckRibHeight"))
        pad(body, "Pad_Splice", rectangle(body, "Sketch_Splice",
            "DeckSpliceLength", "DeckRibWidth"), "DeckSpliceThickness")

    fixture_group = group(doc, "TestFixtures", "03 仅用于单层台架试验的四个支座")
    for number, (x, y) in enumerate((
        ("ColumnCentreOffset", "ColumnCentreOffset"),
        ("ColumnCentreOffset+ColumnPitchX", "ColumnCentreOffset"),
        ("ColumnCentreOffset", "ColumnCentreOffset+ColumnPitchY"),
        ("ColumnCentreOffset+ColumnPitchX", "ColumnCentreOffset+ColumnPitchY"),
    ), 1):
        _, body = part(doc, fixture_group, f"test_support_{number}",
                       f"测试支座 {number}", (x, y, "-DeckFixtureHeight"))
        pad(body, "Pad_Support", circle(body, "Sketch_Support", "CollarRadius", "Zero"),
            "DeckFixtureHeight")
    doc.recompute()
    return doc


def validate_native(doc):
    all_bodies = [obj for obj in doc.Objects if obj.TypeId == "PartDesign::Body"]
    sketches = [obj for obj in doc.Objects if obj.TypeId == "Sketcher::SketchObject"]
    assert len(all_bodies) == 9, len(all_bodies)
    assert sketches and all(s.FullyConstrained for s in sketches)
    assert all(not b.Shape.isNull() and b.Shape.isValid() and len(b.Shape.Solids) == 1
               for b in all_bodies)
    assert not any("Invalid" in obj.State or "Error" in obj.State for obj in doc.Objects)
    return {"bodies": len(all_bodies), "sketches": len(sketches),
            "fully_constrained": True, "single_valid_solid_each": True}


def validate_assembly(doc):
    shapes = {name: global_shape(bodies(p)[0]) for name, p in parts(doc).items()}
    names = list(shapes)
    intersections = []
    for i, first in enumerate(names):
        for second in names[i + 1:]:
            volume = shapes[first].common(shapes[second]).Volume
            if volume > 0.01:
                intersections.append({"a": first, "b": second, "volume_mm3": volume})
    if intersections:
        raise RuntimeError(f"Prototype assembly has interfering solids: {intersections}")
    height = parameters.evaluate(doc, "DeckRibHeight")
    centres = [
            [parameters.evaluate(doc, "ColumnCentreOffset"), parameters.evaluate(doc, "ColumnCentreOffset")],
            [parameters.evaluate(doc, "ColumnCentreOffset+ColumnPitchX"), parameters.evaluate(doc, "ColumnCentreOffset")],
            [parameters.evaluate(doc, "ColumnCentreOffset"), parameters.evaluate(doc, "ColumnCentreOffset+ColumnPitchY")],
            [parameters.evaluate(doc, "ColumnCentreOffset+ColumnPitchX"), parameters.evaluate(doc, "ColumnCentreOffset+ColumnPitchY")],
            ]
    # Quantify the actual solid contact patch at each fixture, including edge notches.
    # The 0.1 mm cylinder slab is used only for checking, never as delivered geometry.
    deck_shapes = [shapes["reinforced_deck_left"], shapes["reinforced_deck_right"]]
    contact = []
    for x, y in centres:
        slab = Part.makeCylinder(parameters.evaluate(doc, "CollarRadius"), 0.1,
                                 App.Vector(x, y, 0))
        area = sum(shape.common(slab).Volume / 0.1 for shape in deck_shapes)
        if area <= 0:
            raise RuntimeError(f"Support at {(x, y)} does not contact deck")
        contact.append(round(area, 3))
    return {"interfering_pairs": [], "support_centres_mm": centres,
            "support_contact_area_mm2": contact, "rib_underhang_mm": height,
            "nominal_local_clearance_mm": parameters.evaluate(doc, "DeckPitch-DeckThickness") - height}


def test_parameter_edit(doc):
    left = doc.getObject("reinforced_deck_left_Body")
    right = doc.getObject("reinforced_deck_right_Body")
    front = doc.getObject("front_splice_Body")
    original = [left.Shape.BoundBox.ZMin, right.Shape.BoundBox.ZMin,
                front.getGlobalPlacement().Base.z]
    parameters.set_value(doc, "DeckRibHeight", "10 mm")
    edited = [left.Shape.BoundBox.ZMin, right.Shape.BoundBox.ZMin,
              front.getGlobalPlacement().Base.z]
    if not all(abs(a - b - 2) < 1e-6 for a, b in zip(edited, original)):
        raise RuntimeError(f"RibHeight expression did not update all parts: {original}, {edited}")
    parameters.set_value(doc, "DeckRibHeight", "12 mm")
    restored = [left.Shape.BoundBox.ZMin, right.Shape.BoundBox.ZMin,
                front.getGlobalPlacement().Base.z]
    if not all(abs(a - b) < 1e-6 for a, b in zip(restored, original)):
        raise RuntimeError("RibHeight could not be restored")
    validate_native(doc)
    return {"parameter": "DeckRibHeight", "before_mm": 12,
            "edited_mm": 10, "after_mm": 12, "two_decks_and_splices_follow": True}


def export_print_stls(doc):
    output = ROOT / "print-stl"
    output.mkdir(parents=True, exist_ok=True)
    records = []
    for name, p in parts(doc).items():
        if name.startswith("test_support_") and name != "test_support_1":
            continue
        body = bodies(p)[0]
        # Export local geometry. Rotate only the reinforced decks 180 degrees about X,
        # placing the broad top surface on the print bed and growing the ribs upward.
        shape = body.Shape.copy()
        if name.startswith("reinforced_deck_"):
            shape.Placement = App.Placement(App.Vector(), App.Rotation(App.Vector(1, 0, 0), 180)).multiply(shape.Placement)
        box = shape.BoundBox
        shape.translate(App.Vector(-box.XMin, -box.YMin, -box.ZMin))
        mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.02,
                                      AngularDeflection=0.15, Relative=False)
        path = output / f"{name}.stl"
        mesh.write(str(path))
        checked = Mesh.Mesh(str(path))
        if not checked.isSolid() or checked.hasNonManifolds() or len(checked.getSeparateComponents()) != 1:
            raise RuntimeError(f"Invalid STL: {path}")
        bb = checked.BoundBox
        dims = [bb.XLength, bb.YLength, bb.ZLength]
        fit = dims[0] + 8 <= 256.001 and dims[1] + 8 <= 256.001 and dims[2] <= 260.001
        if not fit:
            raise RuntimeError(f"X2D build volume with 4 mm brim exceeded: {name}, {dims}")
        records.append({"file": str(path.relative_to(ROOT)), "name": name,
                        "quantity": 4 if name == "test_support_1" else 1,
                        "size_mm": dims, "closed": True, "manifold": True,
                        "x2d_with_4mm_brim": True,
                        "orientation": "broad deck top on bed; ribs upward" if name.startswith("reinforced_deck_") else "flat face on bed"})
    return records


def main():
    doc = build()
    native = validate_native(doc)
    assembly = validate_assembly(doc)
    parameter_test = test_parameter_edit(doc)
    stls = export_print_stls(doc)
    doc.recompute()
    project = ROOT / "GarageDeckRibbedH12.FCStd"
    doc.saveAs(str(project))
    App.closeDocument(doc.Name)
    reopened = App.openDocument(str(project))
    reopened.recompute()
    validate_native(reopened)
    validate_assembly(reopened)
    App.closeDocument(reopened.Name)
    report = {"status": "passed", "freecad_version": App.Version(),
              "project": project.name, "native": native, "assembly": assembly,
              "parameter_edit": parameter_test, "save_close_reopen": "passed",
              "print_stls": stls, "physical_load_test": "not_yet_performed",
              "source_v3_assembly_modified": False}
    (ROOT / "validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
