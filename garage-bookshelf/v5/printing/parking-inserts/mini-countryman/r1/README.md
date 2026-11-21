# MINI Countryman 车型卡槽 · r1

[单件3MF](mini-countryman-r1.3mf)包含一个托座、一个对象、一盘；[可编辑CAD](../../../../cad/parking-inserts/mini-countryman/r1/mini-countryman-r1.FCStd)为独立原生FreeCAD模型。接口为`parking-base-v1`，保留通用底脚和取放耳，板面带同色 **MINI COUNTRYMAN** 凸字。

## 实测输入与派生尺寸

用户于2026-11-11提供[手写测量图片](../../../../assets/measurements/parking-insert-mini-countryman-2026-11-11.jpg)；[原始参数及测量定义](../../../../cad/parking-inserts/mini-countryman/r1/measurements.json)如下，单位mm。S为同侧前轮最前缘到后轮最后缘，Bf/Br为对应轴左右轮胎外侧总宽。

| 参数 | 实测值 |
|---|---:|
| S | 50.6 |
| Bf | 28.8 |
| Br | 27.8 |
| Df | 9.9 |
| Dr | 9.9 |
| Tf | 5.1 |
| Tr | 5.1 |

轴距 **40.7mm**、前轮距 **23.7mm**、后轮距 **22.7mm**。前轮心X=±11.85、后轮心X=±11.35，前后轮心Y=±20.35；前轴在Y正向、取放耳在Y负向。前后不同轮距分别建模。

底脚40×80×2mm、R2，含取放耳总包络40×83×3.6mm。每侧胎宽间隙0.2mm、径向余量0.15mm、侧壁1.2mm，槽高出底板1.6mm，前后槽净宽均5.5mm；重力落座、向上取车。文字字高2.7mm、宽约35.54mm、凸起0.4mm，完整放在底板内。

## 打印与验证

X2D、0.4mm喷嘴、黑色PLA、纹理PEI、0.20mm层高、4圈墙、25%填充、4mm自动brim、无支撑，底脚平放。保存的3MF已独立重开切片，估算 **16.5分钟 / 7.69g**，不含G-code。

2026-11-11检查通过，详见[validation.json](validation.json)和[切片结果](slice-result.json)：

- CAD保存后重开重算有效、单实体、全部9个草图完全约束；七项测量值修改并恢复，派生参数和几何往返检查通过。
- 通用底脚与当前总装双向形状比较满足规范；四个理论轮胎在落座和上抬2mm时无干涉；四层十个车位的干涉检查通过。
- 文字完整受底板支撑，不侵入轮槽；STL封闭、单连通、无非流形，体积误差低于0.1%；3MF尺寸与CAD一致。
- 保存的3MF独立重开切片为一盘一对象，返回码0、模型警告为空。CLI工具消息和模型警告分别记录。

原始日志：[导出](evidence/export.log)、[重开切片](evidence/slice.log)。冻结打印配置、检查用STL和生成脚本快照保存在[evidence/](evidence/)，报告内的哈希和路径对应本款实际交付文件。

**尚未实物打印或试配。** 图片未提供车身、底盘、轮拱净空及车模比例；当前检查覆盖给定轮胎和主体接口，仍需实车模确认落座、取放、滚动或晃动、车身及底盘净空。

[整体预览](tray-preview.png) · [顶视预览](top-preview.png) · [Bambu排盘预览](plate-preview.png) · [CAD输入与复现](../../../../cad/parking-inserts/mini-countryman/r1/README.md)
