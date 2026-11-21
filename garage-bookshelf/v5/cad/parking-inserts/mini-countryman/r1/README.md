# MINI Countryman · r1 原生卡槽CAD

[可编辑FreeCAD源文件](mini-countryman-r1.FCStd)采用`parking-base-v1`和[BMW Z4 E89实测四轮弧形槽方法](../../../../docs/interfaces/parking-inserts.md)。`DesignParameters`控制底脚和取放耳，`WheelFit`保存七项实测值及轮心推导表达式，`ModelLabel`控制车型标记。最终是单个原生Body，全部草图完全约束，轮槽由原生Pad/Pocket建立。

[measurements.json](measurements.json)记录测量定义和输入；[原始用户图片](../../../../assets/measurements/parking-insert-mini-countryman-2026-11-11.jpg)提供S=50.6、Bf=28.8、Br=27.8、Df=Dr=9.9、Tf=Tr=5.1，单位mm。文字为MINI COUNTRYMAN，字高2.7mm、凸起0.4mm；[冻结Arial Bold轮廓](model-label-outline.json)按大写字高归一化，生成时等比缩放。

在`v5/`使用尚未存在的新目录复现：

```sh
/Applications/FreeCAD.app/Contents/Resources/bin/python tools/make_parking_insert.py --spec cad/parking-inserts/mini-countryman/r1/measurements.json --output build/mini-countryman-r1-new-run
```

[单件3MF、验证报告和实物试配状态](../../../../printing/parking-inserts/mini-countryman/r1/README.md)。
