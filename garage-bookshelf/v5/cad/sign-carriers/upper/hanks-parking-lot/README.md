# 上方横牌 · HANK'S PARKING LOT

[原生CAD](hanks-parking-lot.FCStd) · [冻结字形](lettering.json) · [打印项目与验证](../../../../printing/sign-carriers/upper/hanks-parking-lot/README.md)

接口`sign-upper-v1`，继承正式总装的`top_carrier_Body`及M3孔位、厚度和R3外角圆角。文件仅包含一块原生可编辑载板，以局部坐标保存；安装位置及正式总装哈希见打印目录中的`validation.json`。

使用DIN Condensed Bold，文字分为`HANK'S`、`PARKING LOT`两行居中，采用停车场招牌的大写排版。字形高18mm、行间净距8mm，黑底`#16181B`、白字`#F4F5F6`，凸起1mm。

`LetteringParameters`控制字高、行距和凸字深度；`DesignParameters`保留源接口参数。轮廓使用全约束草图和原生Pad，已冻结在`lettering.json`中。更换文字时重新冻结轮廓，不能仅修改文字描述单元格。配色及正面视角已经保存。

在`v5/`中复现，输出目录须为空且位于`build/`：

```sh
/Applications/FreeCAD.app/Contents/Resources/bin/python tools/make_sign_carrier.py --position upper --variant hanks-parking-lot --lettering cad/sign-carriers/upper/hanks-parking-lot/lettering.json --output build/hanks-parking-lot-r2
```

验证范围与实物试装状态见[打印说明](../../../../printing/sign-carriers/upper/hanks-parking-lot/README.md#验证与实物反馈)，原始证据随打印款式保存在其`evidence/`。实际文件位置由该款`validation.json`的`artifact_locations`关联；本目录只维护原生CAD与冻结字形。
