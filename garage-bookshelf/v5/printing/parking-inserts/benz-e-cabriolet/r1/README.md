# Benz E Cabriolet 车型卡槽 · r1

[单件3MF](benz-e-cabriolet-r1.3mf)含一个托座、一个对象、一盘；[可编辑CAD](../../../../cad/parking-inserts/benz-e-cabriolet/r1/benz-e-cabriolet-r1.FCStd)是独立原生FreeCAD模型。接口为`parking-base-v1`，保留既有通用底脚及取放耳，含同色 **BENZ E CABRIOLET** 车型凸字。

## 实测输入与派生尺寸

用户于2026-11-06提供[手写测量图片](../../../../assets/measurements/parking-inserts-2026-11-06.jpg)；[原始参数与测量定义](../../../../cad/parking-inserts/benz-e-cabriolet/r1/measurements.json)如下，单位mm。S为同侧前轮最前缘至后轮最后缘，Bf/Br为对应轴左右轮胎外侧总宽。

| 参数 | 实测值 |
|---|---:|
| S | 39 |
| Bf | 20 |
| Br | 20 |
| Df | 7 |
| Dr | 7 |
| Tf | 2.9 |
| Tr | 2.9 |

轴距 **32mm**，前轮距 **17.1mm**，后轮距 **17.1mm**。轮心在X=±对应轮距/2、Y=±轴距/2；前轴在Y正向，取放耳在Y负向。前后胎宽和轮距分别建模。

底脚40×80×2mm、R2，含取放耳总包络40×83×3.6mm。每侧胎宽间隙0.2mm、径向余量0.15mm、侧壁1.2mm，槽高出底板1.6mm。前槽净宽3.3mm、后槽净宽3.3mm，重力落座、向上取车。车型标记字高2.6mm、宽约35.18mm、凸起0.4mm；长名称等比缩小字高以完整容纳于底板内。

## 打印与验证

X2D、0.4mm喷嘴、黑色PLA、纹理PEI、0.20mm层高、4圈墙、25%填充、4mm自动brim、无支撑，底脚平放。已保存并独立重开切片，估算 **16.5分钟 / 7.63g**，不含G-code。

2026-11-06软件检查通过，详见[validation.json](validation.json)及[切片结果](slice-result.json)：

- CAD重开重算有效、单实体、全部9个草图全约束；七项测量值修改并恢复，派生参数与几何往返检查通过。
- 通用底脚双向形状比较满足规范；四个理论轮胎在落座和上抬2mm时无干涉；四层十车位干涉检查通过。
- 文字完整受底板支撑，不侵入轮槽；STL封闭、单连通、无非流形，体积误差低于0.1%；3MF尺寸与CAD一致。
- 保存的3MF独立重开切片为一对象一盘，返回码0、模型警告为空。原始CLI工具消息与模型警告分别记录。

原始日志：[导出](evidence/export.log)、[重开切片](evidence/slice.log)。实际冻结配置、STL及生成脚本快照保存在[evidence/](evidence/)中；验证报告的哈希和路径对应本款实际交付文件。

**尚未实物打印或试配。** 图片未提供车身、底盘、轮拱净空和车模比例；当前检查覆盖给定轮胎与主体接口，仍需实车模确认落座、取放、滚动或晃动、车身及底盘净空。

[整体预览](tray-preview.png) · [顶视预览](top-preview.png) · [Bambu排盘预览](plate-preview.png) · [输入与复现](../../../../cad/parking-inserts/benz-e-cabriolet/r1/README.md)
