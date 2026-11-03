# 验证进展与待办

资料核对日期：2026-11-04。这里汇总已有验证证据、适用范围与尚缺的实物反馈。各项验证的执行日期以原记录为准，资料核对不代表重新执行验证。

产品配置与款式清单由[CAD索引](cad/README.md)和[打印选型索引](printing/README.md)维护；各款的详细结论与实物反馈记在对应款式说明中。本页在验证结论、已知问题或后续工作发生变化时更新。

## 已有验证证据

| 对象 | 已有证据与适用范围 |
|---|---|
| 正式总装与默认打印件 | [总装验证索引](docs/verification.json)对应当前总装哈希，原生几何、全约束草图、装配净空及连接片检查通过。默认3MF沿用已保存的基线与连接片切片记录，来源见[文件清单](printing/catalog.json)。这些记录不涵盖后来新增的定制款。 |
| 定制文字载板 | 2026-11-03至04日生成的上方、右侧两款已通过原生重开重算、参数往返、接口比较、装配净空、网格、配色及保存后重开3MF切片检查：[上方验证](printing/sign-carriers/upper/lifes-too-short/validation.json)、[右侧验证](printing/sign-carriers/side/engines-roar-pages-whisper/validation.json)。其他款式按[载板索引](printing/sign-carriers/README.md)中的各款记录确认。 |
| BMW Z4 E89车型卡槽 | 当前B28、0.4mm凸字版已有原生参数往返、四轮理论净空、通用底脚比较、十车位干涉、封闭网格及单托座重开切片记录，见[款式说明](printing/parking-inserts/bmw-z4-e89/README.md)与[原始验证](studies/measured-tray-s51-b23-d10-t5p1/validation.json)。理论轮胎净空检查不覆盖实际车身与轮拱。 |

个人调整的3MF另列在对应组件索引中；默认文件的切片结论不能代替个人修改后文件的验证。

## 尚缺的实物反馈

截至核对日期，仓库尚无以下事项的完成记录：

1. 主体接头、柱段和层板的实物干装；饰片齐平安装与粘接效果；背面连接片粘接后的整机承载表现。
2. 默认及定制文字载板的孔位、贴合、文字方向和实际拆换反馈。
3. BMW当前0.4mm凸字版的实物打印与车模试配。已有用户确认针对无字B28版；加字版仍需确认取放、固定及车身净空。

收到实物反馈后，在对应组件或款式说明中记录具体版本和结果，再更新本页。新增文字或车型按[文字载板规范](docs/interfaces/sign-carriers.md)、[车型卡槽规范](docs/interfaces/parking-inserts.md)完成验证与试配；历史实施经过见[CHANGELOG.md](CHANGELOG.md)。
