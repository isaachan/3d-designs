"""Read the saved FCStd (without modifying it) and compare its meshes with STL.
Run with /Applications/FreeCAD.app/Contents/Resources/bin/python.
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, "/Applications/FreeCAD.app/Contents/Resources/lib")
import FreeCAD as App
import Mesh

ROOT = Path(__file__).resolve().parents[1]
doc = App.openDocument(str(ROOT / "bambu-print/garage-bookshelf-v4-装配检查.FCStd"))
result = []

def triangles(mesh):
    return [[list(v) for v in facet.Points] for facet in mesh.Facets]

def canonical(tris):
    return sorted(tuple(sorted(tuple(round(c, 4) for c in v) for v in tri)) for tri in tris)

for obj in doc.Objects:
    if obj.TypeId != "Mesh::Feature":
        continue
    name = obj.Name.lstrip("_")
    local = obj.Mesh.copy()
    local.Placement = App.Placement()
    source = Mesh.Mesh(str(ROOT / "bambu-print/stl" / (name + ".stl")))
    local_tris = triangles(local)
    world_tris = [[list(obj.Placement.multVec(App.Vector(*v))) for v in tri] for tri in local_tris]
    result.append(dict(name=name, label=obj.Label, placement=list(obj.Placement.Matrix.A),
                       facets=local.CountFacets, matches_stl=canonical(local_tris) == canonical(triangles(source)),
                       triangles=world_tris))

(ROOT / "audit/freecad-meshes.json").write_text(json.dumps(result))
print(json.dumps([{k:v for k,v in obj.items() if k != 'triangles'} for obj in result], ensure_ascii=False, indent=2))
App.closeDocument(doc.Name)
