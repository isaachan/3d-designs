"""Confirm that the inspection FCStd uses the independently exported STL meshes."""
import json
from pathlib import Path
import sys

sys.path.insert(0, "/Applications/FreeCAD.app/Contents/Resources/lib")
import FreeCAD as App
import Mesh

ROOT = Path(__file__).resolve().parents[1]
STL = ROOT / "stl"
FCSTD = ROOT / "garage-bookshelf-v2-assembly.FCStd"
OUT = Path(__file__).resolve().parent / "freecad-validation.json"

expected = {f"module_{i}" for i in range(1, 6)}
expected |= {f"garage_deck_{i}_{side}" for i in range(1, 4) for side in ("left", "right")}
expected |= {f"garage_column_{i}" for i in range(1, 5)}
expected.add("book_depot_sign")

doc = App.openDocument(str(FCSTD))
meshes = {obj.Name: obj for obj in doc.Objects if getattr(obj, "TypeId", "") == "Mesh::Feature"}
if set(meshes) != expected:
    raise AssertionError(f"FCStd part set mismatch: missing={expected-set(meshes)}, extra={set(meshes)-expected}")

parts = []
for name in sorted(expected):
    source = Mesh.Mesh(str(STL / f"{name}.stl"))
    obj = meshes[name]
    if obj.Mesh.CountFacets != source.CountFacets:
        raise AssertionError(f"{name}: FCStd facet count does not match STL")
    if not obj.Mesh.isSolid() or len(obj.Mesh.getSeparateComponents()) != 1:
        raise AssertionError(f"{name}: FCStd mesh is not a single closed component")
    parts.append({"name": name, "facets": source.CountFacets, "stl_match": "facet-count"})

OUT.write_text(json.dumps({"status": "passed", "assembly_part_count": len(parts), "parts": parts}, ensure_ascii=False, indent=2))
App.closeDocument(doc.Name)
print(json.dumps({"status": "passed", "assembly_part_count": len(parts)}, ensure_ascii=False))
