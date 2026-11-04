# 上方横牌 · Life's too short to drive boring cars

[原生CAD](lifes-too-short.FCStd) · [冻结字形](lettering.json) · [打印项目](../../../../printing/sign-carriers/upper/lifes-too-short/README.md)

接口为`sign-upper-v1`，继承正式总装的`top_carrier_Body`。本文件只包含这一块文字载板及其原生特征和参数表，不是整机总装副本。配色与视角已经保存，直接打开查看；整机Preview宏用于正式总装。CAD以载板局部坐标保存，安装位置见打印目录中的验证记录。

`DesignParameters`保留源接口参数；`LetteringParameters`控制字形高度、行／列间距和凸起／凹刻深度。文字轮廓由全约束草图和原生Pad/Pocket构成。改变文字内容时重新冻结字形并生成，不能只改参数表中的文字描述单元格。

在`v5/`运行，使用新的输出目录：

```sh
/Applications/FreeCAD.app/Contents/Resources/bin/python tools/make_sign_carrier.py --position upper --variant lifes-too-short --lettering cad/sign-carriers/upper/lifes-too-short/lettering.json --output build/lifes-too-short-r2
```

原生重开重算、字高往返、接口、装配净空、网格及保存3MF重开切片检查均通过；实物试装尚待完成。颜色为黑底白字，文字凸起1mm。
