# MINI Cooper · r1 停车卡槽

卡槽沿用 `parking-base-v1` 接口，含四个弧形轮槽、取放耳和 0.4 mm 高的 **MINI COOPER** 凸字。总尺寸为 40 × 83 × 3.6 mm。[单件 3MF](mini-cooper-r1.3mf) · [可编辑 FreeCAD 模型](../../../../cad/parking-inserts/mini-cooper/r1/mini-cooper-r1.FCStd) · [预览](tray-preview.png)

| 参数 | 建模值（mm） |
|---|---:|
| 同侧前后轮外缘跨度 S | 53.5 |
| 前／后轴轮胎外侧总宽 Bf / Br | 26.5 / 26.5 |
| 前／后胎直径 Df / Dr | 10.2（暂定） / 10.2 |
| 前／后胎宽 Tf / Tr | 4 / 4 |

原图的前胎直径条目被涂掉，本版先采用后胎直径 10.2 mm。按该值推得轴距 43.3 mm，前后轮距均为 22.5 mm，槽内宽均为 4.4 mm。[原始图片](../../../../assets/measurements/parking-insert-mini-cooper-2026-11-15.jpg) · [参数文件](../../../../cad/parking-inserts/mini-cooper/r1/measurements.json)

3MF 预设为 X2D、0.4 mm 喷嘴、黑色 PLA、0.20 mm 层高、4 圈墙、25% 填充，底板平放。重开切片为一盘一对象，约 16.4 分钟、7.65 g，切片结果无模型警告。[切片结果](slice-result.json) · [原始日志](evidence/slice.log)

CAD 重开重算、参数修改与恢复、理论轮胎净空、十车位干涉和网格检查均通过。前胎尺寸与车身、底盘的实际净空仍待实物试配确认。[验证报告](validation.json)
