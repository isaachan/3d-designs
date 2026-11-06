# Teramont Pro · r1 原生卡槽CAD

[可编辑FreeCAD源文件](teramont-pro-r1.FCStd)采用`parking-base-v1`和[BMW Z4 E89实测四轮弧形槽方法](../../../../docs/interfaces/parking-inserts.md)。`DesignParameters`控制底脚和取放耳，`WheelFit`保存七项实测值及推导表达式，`ModelLabel`控制车型标记。最终为一个原生Body，全部草图完全约束，轮槽采用原生Pad/Pocket。

[measurements.json](measurements.json)记录输入与定义；原始值来自[用户手写图片](../../../../assets/measurements/parking-inserts-2026-11-06.jpg)，单位mm：S=57、Bf=30、Br=30、Df=11、Dr=11、Tf=3.2、Tr=3.5。`label_cap_height_mm`为3.2mm，凸起0.4mm；[冻结Arial Bold轮廓](model-label-outline.json)按统一大写字高归一化，生成时按实际字高等比缩放。

Teramont Pro前胎宽采用涂改后清晰标注的3.2mm，后胎宽为独立标注的3.5mm。

在`v5/`使用尚未存在的新目录复现：

```sh
/Applications/FreeCAD.app/Contents/Resources/bin/python tools/make_parking_insert.py --spec cad/parking-inserts/teramont-pro/r1/measurements.json --output build/teramont-pro-r1-new-run
```

[单件3MF、验证报告和实物试配状态](../../../../printing/parking-inserts/teramont-pro/r1/README.md)。
