"""Create a FreeCAD inspection file for the two shortened visual modules."""
from pathlib import Path
import FreeCAD as App
import Mesh

ROOT = Path(__file__).resolve().parent
STL = ROOT / "stl"
OUT = ROOT / "garage-bookshelf-v2-narrow-visual.FCStd"

doc = App.newDocument("GarageBookshelfV2NarrowVisual")
for name, label, x in (
    ("module_2_narrow_visual", "模块 2 缩短外观验证件（不可装配）", 0),
    ("module_5_narrow_visual", "模块 5 缩短外观验证件（不可装配）", 135),
):
    obj = doc.addObject("Mesh::Feature", name)
    obj.Label = label
    obj.Mesh = Mesh.Mesh(str(STL / f"{name}.stl"))
    obj.Placement.Base = App.Vector(x, 0, 0)
    if obj.ViewObject is not None:
        obj.ViewObject.ShapeColor = (0.55, 0.58, 0.62)
        obj.ViewObject.LineColor = (0.2, 0.2, 0.2)
        obj.ViewObject.DisplayMode = "Flat Lines"
doc.recompute()
doc.saveAs(str(OUT))
print(f"Generated {OUT}")
