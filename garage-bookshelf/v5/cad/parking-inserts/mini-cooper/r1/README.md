# MINI Cooper · r1 原生 CAD

卡槽采用 `parking-base-v1` 接口。FreeCAD 的 `WheelFit` 保留轮胎输入和轮心推导表达式，`ModelLabel` 控制字高与凸起。四个弧形轮槽和车型文字均可编辑。[FreeCAD 模型](mini-cooper-r1.FCStd) · [冻结字形](model-label-outline.json)

图片中的前胎直径 Df 被涂掉，r1 暂按后胎直径 10.2 mm 建模。确认前胎直径后，可在 `WheelFit.FrontDiameter` 修正。原始输入和假设均已记录。[测量参数](measurements.json) · [原始图片](../../../../assets/measurements/parking-insert-mini-cooper-2026-11-15.jpg)

在 `v5/` 中运行以下命令复现。

```sh
/Applications/FreeCAD.app/Contents/Resources/bin/python tools/make_parking_insert.py --spec cad/parking-inserts/mini-cooper/r1/measurements.json --output build/mini-cooper-r1-new-run
```

[打印文件与试配状态](../../../../printing/parking-inserts/mini-cooper/r1/README.md)
