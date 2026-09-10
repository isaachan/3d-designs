"""生成车库书架 v4 的 FreeCAD 装配检查文件。

运行方式（安装 FreeCAD 后）：
FreeCADCmd generate-freecad-assembly.py
或在 FreeCAD 的“宏”窗口运行本文件。
"""

from pathlib import Path

import FreeCAD as App
import Mesh

try:
    import FreeCADGui as Gui
except ImportError:
    Gui = None


# `__file__` is absent when FreeCAD runs this through its Python console.
ROOT = Path(globals().get("__file__", "/Users/kai.han/code/3d-designs/garage-bookshelf/bambu-print/generate-freecad-assembly.py")).resolve().parent
STL = ROOT / "stl"
OUT = ROOT / "garage-bookshelf-v4-装配检查.FCStd"

GRAY = (0.55, 0.58, 0.62)
YELLOW = (0.98, 0.72, 0.10)
BLACK = (0.08, 0.09, 0.11)
BLUE = (0.10, 0.36, 0.88)
WHITE = (0.95, 0.95, 0.95)

doc = App.newDocument("GarageBookshelfV4Assembly")


def group(label):
    item = doc.addObject("App::DocumentObjectGroup", label.replace(" ", "_"))
    item.Label = label
    return item


def rotation(axis, angle):
    return App.Rotation(App.Vector(*axis), angle)


def add_mesh(parent, filename, label, base, rotate, color):
    source = STL / filename
    obj = doc.addObject("Mesh::Feature", filename.removesuffix(".stl"))
    obj.Label = label
    obj.Mesh = Mesh.Mesh(str(source))
    obj.Placement = App.Placement(App.Vector(*base), rotate)
    if obj.ViewObject is not None:
        obj.ViewObject.ShapeColor = color
        obj.ViewObject.LineColor = (0.2, 0.2, 0.2)
        obj.ViewObject.DisplayMode = "Flat Lines"
    parent.addObject(obj)
    return obj


base_group = group("01 底板（灰色）")
back_group = group("02 背板与连接片（灰色）")
panel_group = group("03 竖板与加强肋（灰色）")
garage_group = group("04 停车场层板与立柱")
billboard_group = group("05 广告牌（黑色）")
sign_group = group("06 BOOK DEPOT（蓝色和白色）")

# 坐标约定：X 为总长 920 mm，Y 为前后深度 220 mm，Z 为高度。
# 01：四段底板，拼成 920 × 220 × 8 mm。
for index, x in enumerate((0, 230, 460, 690), start=1):
    add_mesh(base_group, f"01_base_{index:02}.stl", f"底板 {index}/4", (x, 0, 0), App.Rotation(), GRAY)

# 02：八块背板。局部 Y 轴旋转到全局 Z 轴，局部厚度在全局 Y 方向。
back_rotation = rotation((1, 0, 0), 90)
for row, z in enumerate((8, 158), start=1):
    for col, x in enumerate((0, 230, 460, 690), start=1):
        add_mesh(back_group, f"02_back_r{row}_c{col}.stl", f"背板 第{row}行 第{col}列", (x, 220, z), back_rotation, GRAY)

# 背板连接片：前六片覆盖两行的三条竖缝，后四片覆盖中部横缝。
for index in range(1, 7):
    row = 0 if index <= 3 else 1
    seam = (index - 1) % 3
    x = (230, 460, 690)[seam] - 25
    z = (8, 158)[row] + 58
    add_mesh(back_group, f"03_back_join_plate_{index:02}.stl", f"背板竖缝连接片 {index}", (x, 223, z), back_rotation, GRAY)
for index, x in enumerate((90, 320, 550, 780), start=7):
    add_mesh(back_group, f"03_back_join_plate_{index:02}.stl", f"背板横缝连接片 {index}", (x, 223, 140), back_rotation, GRAY)

# 03：中隔板与右侧板。局部 x→全局 y、局部 y→全局 z、局部 z→全局 x。
panel_rotation = rotation((1, 1, 1), 120)
for prefix, label, x in (("04_divider", "中隔板", 360), ("05_right_panel", "右侧板", 914)):
    add_mesh(panel_group, f"{prefix}_lower.stl", f"{label} 下段", (x, 0, 8), panel_rotation, GRAY)
    add_mesh(panel_group, f"{prefix}_upper.stl", f"{label} 上段", (x, 0, 158), panel_rotation, GRAY)

# Splice plates sit on the book-side faces and bridge the Z=158 mm joints.
add_mesh(panel_group, "04_divider_vertical_join_plate.stl", "中隔板 书侧连接片", (366, 75, 123), panel_rotation, GRAY)
add_mesh(panel_group, "05_right_panel_vertical_join_plate.stl", "右侧板 书侧连接片", (911, 75, 123), panel_rotation, GRAY)

# 四个底部加强肋：两个在中隔板根部，两个在右侧板根部。
rib_positions = ((366, 12, 8), (366, 183, 8), (914, 12, 8), (914, 183, 8))
for index, position in enumerate(rib_positions, start=1):
    add_mesh(panel_group, f"08_reinforcing_rib_{index}.stl", f"三角加强肋 {index}/4", position, App.Rotation(), GRAY)

# 04：三层停车层板，每层由左右两片及背面连接片构成；底板就是第一层。
for deck, z in enumerate((66, 129, 192), start=1):
    add_mesh(garage_group, f"06_garage_deck_{deck}_left.stl", f"停车层板 第{deck}层 左", (0, 0, z), App.Rotation(), GRAY)
    add_mesh(garage_group, f"06_garage_deck_{deck}_right.stl", f"停车层板 第{deck}层 右", (180, 0, z), App.Rotation(), GRAY)
    add_mesh(garage_group, f"06_garage_deck_{deck}_join_plate.stl", f"停车层板 第{deck}层 连接片", (159, 50, z - 3), App.Rotation(), GRAY)

for index, (x, y) in enumerate(((0, 0), (330, 0), (0, 185), (330, 185)), start=1):
    add_mesh(garage_group, f"07_yellow_column_{index}.stl", f"黄色承重柱 {index}/4", (x, y, 8), App.Rotation(), YELLOW)

for side, y in (("front", 0), ("rear", 195)):
    add_mesh(garage_group, f"14_garage_header_{side}_left.stl", f"{side} 车库顶梁 左", (0, y, 258), App.Rotation(), GRAY)
    add_mesh(garage_group, f"14_garage_header_{side}_right.stl", f"{side} 车库顶梁 右", (180, y, 258), App.Rotation(), GRAY)
    add_mesh(garage_group, f"14_garage_header_{side}_join_plate.stl", f"{side} 车库顶梁连接片", (159, y, 255), App.Rotation(), GRAY)

# 05：广告牌在背板上方，三片横向拼接；两根柱直接粘在背板上。
for index, x in enumerate((200, 374, 548), start=1):
    add_mesh(billboard_group, f"09_billboard_{index}.stl", f"广告牌 面板 {index}/3", (x, 220, 420), back_rotation, BLACK)
for index, x in enumerate((352, 526), start=1):
    add_mesh(billboard_group, f"09_billboard_join_plate_{index}.stl", f"广告牌 背面连接片 {index}/2", (x, 223, 436), back_rotation, BLACK)
for index, x in enumerate((250, 520), start=1):
    add_mesh(billboard_group, f"10_billboard_post_{index}.stl", f"广告牌平面支柱 {index}/2", (x, 226, 300), back_rotation, BLACK)

# 06：右侧外贴竖牌与白色立体字，均朝向书架前方。
add_mesh(sign_group, "11_book_depot_sign.stl", "BOOK DEPOT 蓝色底牌", (920, 6, 50), back_rotation, BLUE)
add_mesh(sign_group, "12_billboard_text_lovely_car_ive_driven.stl", "广告牌白色文字", (240, 214, 426), back_rotation, WHITE)
add_mesh(sign_group, "13_sign_text_book_depot.stl", "BOOK DEPOT 白色文字", (920, 0, 50), back_rotation, WHITE)

doc.recompute()
doc.saveAs(str(OUT))
if Gui is not None and hasattr(Gui, "activeDocument") and Gui.activeDocument() is not None:
    Gui.activeDocument().activeView().viewAxonometric()
    Gui.activeDocument().activeView().fitAll()
print(f"已生成：{OUT}")
