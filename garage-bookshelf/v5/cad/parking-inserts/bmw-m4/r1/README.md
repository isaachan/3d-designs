# BMW M4 · r1 原生卡槽CAD

[可编辑FreeCAD源文件](bmw-m4-r1.FCStd)使用`parking-base-v1`接口，按[BMW Z4 E89实测四轮弧形槽方法](../../../../docs/interfaces/parking-inserts.md)独立建模。`DesignParameters`控制通用底脚，`WheelFit`保存七项实测值并推导轮心，`ModelLabel`控制车型文字的字高、凸起高度和位置；全部草图完全约束，最终为单个原生Body。

输入为[measurements.json](measurements.json)，原始数据来自[用户手写测量图片](../../../../assets/measurements/parking-inserts-2026-11-04.jpg)，单位mm：S=55、Bf=32、Br=32、Df=11.1、Dr=11.1、Tf=4.2、Tr=4.8。冻结Arial Bold字形保存在[model-label-outline.json](model-label-outline.json)，更改文字后需要重新冻结轮廓。

从`v5/`在尚未使用的新目录复现：

```sh
/Applications/FreeCAD.app/Contents/Resources/bin/python tools/make_parking_insert.py --spec cad/parking-inserts/bmw-m4/r1/measurements.json --output build/bmw-m4-r1-new-run
```

[单件3MF、验证报告及试配状态](../../../../printing/parking-inserts/bmw-m4/r1/README.md)。本源文件不替代整机总装，也不改写已有车型卡槽。
