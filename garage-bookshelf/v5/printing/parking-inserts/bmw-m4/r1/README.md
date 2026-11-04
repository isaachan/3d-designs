# BMW M4 车型卡槽 · r1

[单件3MF](bmw-m4-r1.3mf)含一个托座、一个对象、一盘；[可编辑CAD](../../../../cad/parking-inserts/bmw-m4/r1/bmw-m4-r1.FCStd)为独立原生FreeCAD模型。接口为`parking-base-v1`，保留现有底脚和取放耳，板面含0.4mm高 **BMW M4** 同色凸字。

## 实测输入

用户于2026-11-04提供[手写测量图片](../../../../assets/measurements/parking-inserts-2026-11-04.jpg)。[测量原始值与定义](../../../../cad/parking-inserts/bmw-m4/r1/measurements.json)如下，单位mm；S为同侧前轮最前缘到后轮最后缘，Bf/Br为对应轴左右轮胎外侧总宽。

| 参数 | 实测值 |
|---|---:|
| S | 55 |
| Bf | 32 |
| Br | 32 |
| Df | 11.1 |
| Dr | 11.1 |
| Tf | 4.2 |
| Tr | 4.8 |

派生轴距 **43.9mm**，前轮距 **27.8mm**，后轮距 **27.2mm**。前后轮尺寸分别建模；轮心位于X=±对应轮距/2、Y=±轴距/2，前轴在Y正向、取放耳在Y负向。

底脚40×80×2mm、R2，含取放耳总包络40×83×3.6mm。轮胎每侧间隙0.2mm、径向余量0.15mm、侧壁1.2mm，槽高出板面1.6mm；前槽净宽4.6mm、后槽净宽5.2mm。采用重力落座，向上取车。

## 打印与检查

X2D、0.4mm喷嘴、黑色PLA、纹理PEI、0.20mm层高、4圈墙、25%填充、4mm自动brim、无支撑，底脚平放。保存的3MF已独立重开切片，估算 **16.3分钟 / 7.65g**，不含G-code。

2026-11-04完成以下软件检查，详见[validation.json](validation.json)和[切片结果](slice-result.json)：

- CAD保存后重开重算、单实体、全部9个草图全约束；七项测量输入同时修改后检查派生值和轮胎净空，恢复后双向形状差为零。
- 通用底脚与当前正式总装双向形状差为零；四个轮胎在落座和上抬2mm时无干涉；四层十个车位无实体干涉。
- STL封闭、单连通、无非流形，体积误差低于0.1%；3MF尺寸与CAD一致，重开切片为一盘一对象，模型警告为空。

原始CLI日志见[evidence/export.log](evidence/export.log)与[evidence/slice.log](evidence/slice.log)，实际冻结配置、检查STL和生成脚本快照也在[evidence/](evidence/)。CLI包含系统预设名称查找和T65279/T65535解析消息；保存项目内的完整X2D设置已核对，切片返回码为0。这些工具消息与模型警告分别记录。

**实物状态：尚未打印或试配。** 图片未提供车身、底盘、轮拱净空和车模比例，当前检查只覆盖给定轮胎与主体接口；需要实车模确认落座、取放、滚动和晃动情况、车身及底盘净空。

[整体预览](tray-preview.png) · [顶视预览](top-preview.png) · [Bambu排盘预览](plate-preview.png) · [CAD输入与复现](../../../../cad/parking-inserts/bmw-m4/r1/README.md)
