"""Build the v2 inspection assembly from the independently generated STL files."""
from pathlib import Path
import FreeCAD as App
import Mesh

ROOT = Path(__file__).resolve().parent
STL, OUT = ROOT / "stl", ROOT / "garage-bookshelf-v2-assembly.FCStd"
GRAY, YELLOW, BLUE = (0.55,0.58,0.62), (0.98,0.72,0.10), (0.10,0.36,0.88)

doc = App.newDocument("GarageBookshelfV2")

def group(label):
    obj=doc.addObject("App::DocumentObjectGroup",label.replace(" ","_"));obj.Label=label;return obj

def add(parent, name, label, color, base=(0,0,0), rotation=None):
    obj=doc.addObject("Mesh::Feature",name)
    obj.Label=label;obj.Mesh=Mesh.Mesh(str(STL/f"{name}.stl"))
    obj.Placement=App.Placement(App.Vector(*base), rotation or App.Rotation())
    if obj.ViewObject is not None:
        obj.ViewObject.ShapeColor=color;obj.ViewObject.LineColor=(.2,.2,.2);obj.ViewObject.DisplayMode="Flat Lines"
    parent.addObject(obj);return obj

modules=group("01 五个一体主体模块（灰色）")
for i in range(1,6): add(modules,f"module_{i}",f"主体模块 {i}",GRAY)

garage=group("02 车库层板与立柱")
for level in range(1,4):
    add(garage,f"garage_deck_{level}_left",f"停车层板 {level} 左",GRAY)
    add(garage,f"garage_deck_{level}_right",f"停车层板 {level} 右",GRAY)
for index,(x,y) in enumerate(((0,0),(330,0),(0,185),(330,185)),1):
    add(garage,f"garage_column_{index}",f"黄色承托柱 {index}",YELLOW,(x,y,0))

sign=group("03 右侧竖牌")
add(sign,"book_depot_sign","BOOK DEPOT 蓝色底牌",BLUE,(920,6,50),App.Rotation(App.Vector(1,0,0),90))
doc.recompute();doc.saveAs(str(OUT));print(f"Generated {OUT}")
