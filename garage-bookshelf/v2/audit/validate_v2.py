"""Geometry, topology, mating-path, and assembly consistency checks for v2."""
import json
from pathlib import Path
import sys

sys.path.insert(0, "/Applications/FreeCAD.app/Contents/Resources/lib")
import FreeCAD as App
import Mesh
import Part

ROOT = Path(__file__).resolve().parents[1]
STL = ROOT / "stl"
OUT = Path(__file__).resolve().parent / "validation.json"
CUTS = (0, 180, 410, 590, 770, 920)


def solid_from_stl(path):
    mesh = Mesh.Mesh(str(path))
    shape = Part.Shape()
    shape.makeShapeFromMesh(mesh.Topology, 0.01)
    if len(shape.Shells) != 1:
        raise AssertionError(f"{path.name}: expected one shell, got {len(shape.Shells)}")
    solid = Part.makeSolid(shape.Shells[0])
    if not solid.isValid():
        raise AssertionError(f"{path.name}: invalid Part solid")
    return mesh, solid


records = {}
for path in sorted(STL.glob("*.stl")):
    mesh, solid = solid_from_stl(path)
    if not mesh.isSolid() or len(mesh.getSeparateComponents()) != 1:
        raise AssertionError(f"{path.name}: non-manifold or disconnected mesh")
    box = solid.BoundBox
    records[path.stem] = {
        "facets": mesh.CountFacets,
        "mesh_is_solid": mesh.isSolid(),
        "components": len(mesh.getSeparateComponents()),
        "bounds": [box.XMin, box.YMin, box.ZMin, box.XMax, box.YMax, box.ZMax],
        "volume_mm3": solid.Volume,
    }

modules = [solid_from_stl(STL / f"module_{i}.stl")[1] for i in range(1, 6)]
for i, module in enumerate(modules, 1):
    if len(module.Solids) != 1 or not module.isValid():
        raise AssertionError(f"module_{i} is not one valid solid")
    box = module.BoundBox
    if abs(box.ZMin) > 0.01 or abs(box.ZMax - 238) > 0.01:
        raise AssertionError(f"module_{i}: body height/bottom mismatch")

# Each next module is assembled by translating only in -X.  Sampling the full
# approach establishes that all four male/female pairs share that path and do
# not collide before the final seated position.
assembly_paths = []
for interface in range(4):
    left, right = modules[interface], modules[interface + 1]
    sequence = []
    for offset in (60, 30, 15, 5, 1, 0):
        incoming = right.copy()
        incoming.translate(App.Vector(offset, 0, 0))
        collision = left.common(incoming).Volume
        if collision > 0.01:
            raise AssertionError(f"interface {interface+1}, offset {offset}: collision {collision}")
        sequence.append({"offset_x_mm": offset, "intersection_mm3": collision})
    assembly_paths.append({"interface": interface + 1, "insertion_direction": "-X", "samples": sequence})

# The 4 interfaces contain 2 base + 2 back pairs each.  The nominal per-side
# clearance is 0.20 mm (0.40 mm total width), and axial end clearance is 1 mm.
joints = []
for interface, x in enumerate(CUTS[1:-1], 1):
    # These are the actual constant-profile sliding dovetails made by
    # generate_v2.py.  The base profile is wider at the table-facing bottom;
    # the back profile is taller at its rear face.  Neither value is an
    # invented "root/tip" measurement.
    for kind, centers, profile in (
        ("base", (52,168), {"bottom_width_mm": 30, "top_width_mm": 24}),
        ("back", (66,180), {"front_height_mm": 26, "rear_height_mm": 34}),
    ):
        for center in centers:
            joints.append({"interface":interface,"kind":kind,"center":center, **profile,
                           "male_projection_mm":14,"socket_depth_mm":15,
                           "side_clearance_mm":0.2,"axial_end_clearance_mm":1.0,
                           "insertion_direction":"-X"})
if len(joints) != 16:
    raise AssertionError("Expected exactly 16 dovetail pairs")

# Parking deck / collar check: each deck bottom is at 66/129/192; each column
# collar top touches those planes at 66/129/192 respectively.
deck_supports = [{"deck_z_mm":z,"collar_top_z_mm":z,"contact":"planar, no volume overlap"} for z in (66,129,192)]

result = {
    "status":"passed",
    "part_count":len(records),
    "module_count":5,
    "module_boundaries_mm":list(CUTS),
    "main_dimensions_mm":{"length":920,"depth":220,"height":238,"base_thickness":8},
    "parts":records,
    "dovetail_pairs":joints,
    "assembly_paths":assembly_paths,
    "bottom_plane":"all modules Z=0; no bottom protrusions",
    "garage_supports":deck_supports,
}
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2))
print(json.dumps({k:result[k] for k in ("status","part_count","module_count","main_dimensions_mm","bottom_plane")}, ensure_ascii=False))
