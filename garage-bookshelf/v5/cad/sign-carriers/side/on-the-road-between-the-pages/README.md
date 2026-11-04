# 右侧竖牌 · On the Road. Between the Pages.

[原生CAD](on-the-road-between-the-pages.FCStd) · [冻结字形](lettering.json) · [打印项目与验证](../../../../printing/sign-carriers/side/on-the-road-between-the-pages/README.md)

接口`sign-side-v1`，继承正式总装的`side_cartridge_Body`及M3孔位、厚度和R3外角圆角。文件仅包含一块原生可编辑载板，以局部坐标保存；安装位置及正式总装哈希见打印目录中的`validation.json`。

使用DIN Condensed Bold，保留标题式大小写和两个句点，分为`On the Road.`、`Between the Pages.`两列。字形顺时针转90°，从正面看右列为第一句、左列为第二句，各列沿长度居中。字形高16mm、列间净距6mm，深蓝底`#151B65`、白字`#F4F5F6`，凹刻0.4mm。

`LetteringParameters`控制字高、列距和凹刻深度；`DesignParameters`保留源接口参数。轮廓使用全约束草图和原生Pocket，已冻结在`lettering.json`中。更换文字时重新冻结轮廓，不能仅修改文字描述单元格。配色及正面视角已经保存。

在`v5/`中复现，输出目录须为空且位于`build/`：

```sh
/Applications/FreeCAD.app/Contents/Resources/bin/python tools/make_sign_carrier.py --position side --variant on-the-road-between-the-pages --lettering cad/sign-carriers/side/on-the-road-between-the-pages/lettering.json --output build/on-the-road-between-the-pages-r2
```

验证范围与实物试装状态见[打印说明](../../../../printing/sign-carriers/side/on-the-road-between-the-pages/README.md#验证与实物反馈)，原始证据随打印款式保存在其`evidence/`。实际文件位置由该款`validation.json`的`artifact_locations`关联；本目录只维护原生CAD与冻结字形。
