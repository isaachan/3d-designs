# v3 验证报告（2026-10-20）

重建的原生CAD几何/编辑功能通过；产品功能保留了v2原有设计干涉，不能标为全部装配验收通过。

| 检查 | 结论 | 证据 |
|---|---|---|
| 34个逻辑件/52个独立Body | 通过 | 正式44、辅助8；无新增产品结构 |
| 草图完全约束 | 通过 | 共251张；逐张检查FullyConstrained及约束/Expression |
| 原生建模历史 | 通过 | Sketch/Pad/Pocket/AdditiveLoft/SubtractiveLoft，无静态最终Shape特征 |
| 34件新旧精确几何 | 通过 | 双向布尔差<0.0001mm³，旧网格误差阈值见下 |
| 真实参数修改与恢复 | 通过 | 底厚、层板厚、配合间隙、整体深度，关联零件/装配同步 |
| 保存关闭重开再编辑 | 通过 | 两份工程单Solid有效；主工程重开后重复参数编辑 |
| 主体及层板共同−X插入路径 | 通过 | 4个主体接缝×6位置、3个层板接缝×5位置 |
| STL封闭、非流形、尺寸/包络 | 通过 | 34原坐标+34归零打印+52单Body STL；每岛封闭 |
| 全产品无实体干涉 | 失败（原设计问题） | 几何保留，未擅自补孔/移柱 |
| 实际PLA试配/胶粘强度/承重 | 无法确认 | 没有实物试验；没有编造最小壁厚与认证载荷 |

## 几何比较

旧网格比较：包围盒与抽样面偏差≤0.02mm，体积/表面积相对差≤0.05%。对旧脚本独立精确参考执行双向布尔差，避免仅凭网格包围盒验收。曲面网格三角化与STL float精度单独计入偏差。旧Mesh.Volume对全局文字多实体有数值消减误差，采用局部原点双精度有向三角体积和。OCC默认BoundBox可能包含切槽Loft的未用控制点，使用optimalBoundingBox计算真实边界。

| 零件 | 布尔差mm³ | 网格边界最大差mm | 体积差% | 抽样表面差mm |
|---|---:|---:|---:|---:|
| module_1 | 0 | 2.951758e-06 | 9.028725e-07 | 2.141233e-05 |
| module_2 | 0 | 1.230703e-05 | 1.129597e-06 | 1.484131e-05 |
| module_3 | 0 | 1.230703e-05 | 2.235469e-07 | 1.234626e-05 |
| module_4 | 0 | 1.230703e-05 | 2.055595e-07 | 1.422914e-05 |
| module_5 | 0 | 1e-07 | 1.448199e-06 | 3.032323e-05 |
| garage_deck_1_left | 0 | 2.951758e-06 | 2.002955e-05 | 0.00407416 |
| garage_deck_1_right | 0 | 1e-07 | 6.06416e-06 | 0.005038674 |
| garage_deck_1_seam_bridge | 0 | 0 | 0 | 0 |
| garage_deck_2_left | 0 | 2.951758e-06 | 1.997946e-05 | 0.004064496 |
| garage_deck_2_right | 0 | 1e-07 | 3.690795e-05 | 0.008510284 |
| garage_deck_2_seam_bridge | 0 | 0 | 0 | 0 |
| garage_deck_3_left | 0 | 2.951758e-06 | 1.997946e-05 | 0.004064496 |
| garage_deck_3_right | 0 | 1e-07 | 3.690795e-05 | 0.008510284 |
| garage_deck_3_seam_bridge | 0 | 0 | 0 | 0 |
| garage_column_1 | 0 | 0.001317124 | 0.0190532 | 0.002968272 |
| garage_column_2 | 0 | 0.001317124 | 0.0190532 | 0.002968272 |
| garage_column_3 | 0 | 0.001317124 | 0.0190532 | 0.002968272 |
| garage_column_4 | 0 | 0.001317124 | 0.0190532 | 0.002968272 |
| book_depot_sign | 0 | 3.652753e-15 | 0 | 3.652753e-15 |
| billboard_left | 0 | 0 | 0 | 0 |
| billboard_right | 0 | 0 | 0 | 0 |
| billboard_seam_bridge | 0 | 0 | 0 | 0 |
| billboard_post_left | 0 | 0 | 0 | 0 |
| billboard_post_right | 0 | 0 | 0 | 0 |
| billboard_text_lovely_cars | 0 | 1.220703e-05 | 0.0002314521 | 1.220703e-05 |
| billboard_text_ive_driven | 0 | 1.220703e-05 | 0.0001816794 | 1.220703e-05 |
| test_base_male | 0 | 2.951758e-06 | 6.929965e-07 | 3.051758e-06 |
| test_base_female | 0 | 1e-07 | 2.06033e-07 | 2.266159e-06 |
| test_back_male | 0 | 3.151758e-06 | 2.465098e-06 | 4.943302e-06 |
| test_back_female | 0 | 1e-07 | 1.692336e-06 | 4.958991e-06 |
| test_corner_left_four_male | 0 | 2.951758e-06 | 2.260613e-06 | 1.313793e-05 |
| test_corner_right_four_female | 0 | 1e-07 | 1.69399e-06 | 3.032323e-05 |
| module_2_narrow_visual | 0 | 1.230703e-05 | 1.853821e-06 | 2.241291e-05 |
| module_5_narrow_visual | 0 | 1e-07 | 3.1346e-06 | 3.032323e-05 |

## 保留的原设计干涉

下表是新模型计算值；因精确布尔对照通过，对应形态来自v2。它们不是迁移引入的改动。

| 零件A | 零件B | 穿插体积mm³ |
|---|---|---:|
| module_1 | garage_deck_1_left | 0.200000 |
| module_1 | garage_deck_1_right | 13.800000 |
| module_1 | garage_deck_3_left | 0.042220 |
| module_1 | garage_deck_3_right | 0.499924 |
| garage_deck_1_left | garage_column_1 | 565.486678 |
| garage_deck_1_left | garage_column_3 | 565.486678 |
| garage_deck_2_left | garage_column_1 | 565.486678 |
| garage_deck_2_left | garage_column_3 | 565.486678 |
| garage_deck_3_left | garage_column_1 | 565.486678 |
| garage_deck_3_left | garage_column_3 | 565.486678 |

## 参数编辑证据

- BaseThickness：8.0→9.0mm；核对9项关联行为；恢复最大体积差0mm³。
- DeckThickness：5.0→6.0mm；核对6项关联行为；恢复最大体积差0mm³。
- FitClearance：0.4→0.5mm；核对4项关联行为；恢复最大体积差0mm³。
- OverallDepth：220.0→222.0mm；核对6项关联行为；恢复最大体积差0mm³。

## GUI 验收

已在FreeCAD 1.1.3实际进入Sketch、Pad和Spreadsheet编辑器，并通过GUI保存、关闭、重开检查。详见gui-validation.json。自动辅助功能读树曾触发本机Qt QAccessible缓存崩溃；审阅宏仅在当前GUI进程停用辅助功能更新并延迟运行，正常手工打开工程不需要该宏。

## 范围限制

抽样网格距离不是全表面Hausdorff证明；精确源模型的布尔差覆盖实体几何一致性。打印STL封闭不等于切片/实物验证。原侧牌的位置、层板缺口、像素字形与渐变燕尾均按实际设计保留。详细对象列表、位姿、所有参数及旧文件SHA256另见JSON。
