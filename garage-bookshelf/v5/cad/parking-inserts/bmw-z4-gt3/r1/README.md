# BMW Z4 GT3 · r1 原生 CAD

卡槽采用 `parking-base-v1` 接口。FreeCAD 的 `WheelFit` 保留实测轮胎参数和轮心位置的推导表达式，`ModelLabel` 控制字高及凸起。[可编辑 FreeCAD 模型](bmw-z4-gt3-r1.FCStd) · [冻结字形](model-label-outline.json)

使用手写图片中 BMW Z4 GT3 标题下的尺寸。轴距为 37.2 mm，前轮距为 26.5 mm，后轮距为 26.9 mm。[测量参数](measurements.json) · [原始图片](../../../../assets/measurements/parking-insert-bmw-z4-gt3-2026-11-18.jpg)

在 `v5/` 中运行以下命令复现。

```sh
/Applications/FreeCAD.app/Contents/Resources/bin/python tools/make_parking_insert.py --spec cad/parking-inserts/bmw-z4-gt3/r1/measurements.json --output build/bmw-z4-gt3-r1-new-run
```

[打印文件与试配状态](../../../../printing/parking-inserts/bmw-z4-gt3/r1/README.md)
