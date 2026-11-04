# 上方横牌 · LIFE'S TOO SHORT TO DRIVE BORING CARS · r2

[原生CAD](lifes-too-short.FCStd) · [冻结字形与排版](lettering.json) · [打印项目与验证](../../../../printing/sign-carriers/upper/lifes-too-short/README.md)

当前为r2运动字体版。上行`LIFE'S TOO SHORT TO DRIVE`使用Avenir Next Demi Bold，字形高8mm，中心位于局部坐标(95,43)mm；下行`BORING CARS`使用Avenir Next Condensed Heavy Italic，字形高20.5mm，中心(95,20)mm。两行均为大写，以小标题和大号粗斜体建立层次。深蓝底`#151B65`、白字`#F4F5F6`，凸字1mm。

接口`sign-upper-v1`，继承正式总装的`top_carrier_Body`及M3孔位、1.4mm底板和R3外角圆角。此文件仅包含一块原生可编辑载板，以局部坐标保存；源总装哈希、安装位置及验证见打印目录中的`validation.json`。

`LetteringParameters`中的`Line1Height`、`Line2Height`控制两行字高，`Line1CenterX/Z`、`Line2CenterX/Z`控制各行位置；两行高度均关联`InkHeight`，可一起按比例调整。`TextDepth`控制凸字深度。字形使用全约束草图、原生绑定轮廓与Pad，不依赖字体文件重算。冻结输入记录两种实际字体、原始字体集合哈希及字体集合中的序号；换文字须重新冻结轮廓。轮廓按制造精度去除冗余微小线段，两行在设计字高下相对字体的边界偏差上界均小于0.03mm；简化保持字形孔洞，并在冻结输入中记录实测边界距离及顶点数。

在`v5/`中复现，使用新的空输出目录：

```sh
/Applications/FreeCAD.app/Contents/Resources/bin/python tools/make_sign_carrier.py --position upper --variant lifes-too-short --lettering cad/sign-carriers/upper/lifes-too-short/lettering.json --output build/lifes-too-short-r2-rebuild
```

r1原CAD、字形及打印交付原样保存在[旧版归档](../../../../archive/printing/2026-11-04-lifes-too-short-r1/README.md)。r2的软件验证范围和实物试装状态见[打印说明](../../../../printing/sign-carriers/upper/lifes-too-short/README.md)。
