# 打印生成指南（项目维护者）

选择现成打印文件请到[打印入口](../printing/README.md)。本页说明修改CAD后如何重新生成和准备交付；拼装步骤见[组装说明](assembly.md)。

## 组件与打印配置

主体40件、14盘；两块默认文字载板各1件、各1盘。车型卡槽按需选择和生成，不在整机42件内。盘号是稳定标识，按组件分类后仍保留原盘号。

| 打印对象 | 当前设置 |
|---|---|
| 主体05/06黑色书架 | 0.20mm、4圈墙、25%填充、仅热床支撑 |
| 主体13–15饰片，每色4片 | 0.20mm、3圈墙、0.60mm全厚，无支撑、无擦料塔 |
| 主体16连接片，4片 | 黑色PLA、0.20mm、4圈墙、100%填充、无支撑 |
| 其他主体盘及默认文字载板 | 沿用交付3MF中的设置与配色，完整排盘计划见`printing/plate-plan.json` |
| 车型卡槽试配 | 严格使用[卡槽规范](interfaces/parking-inserts.md)中的层板＋托座方法和设置 |

默认16盘的基线切片估算约43小时33分、1942.4g；按80元/kg约155.39元，不含车型卡槽、外购件、胶、电费、人工和损耗。个人修改过的盘以自己的切片为准。

## 完整重新生成

按[维护指南](maintenance.md)准备环境，在`v5/`目录执行。示例运行名`handover-r1`必须尚未使用；再次生成时换一个名字。

```sh
/Applications/FreeCAD.app/Contents/Resources/bin/python tools/export.py --output build/handover-r1/export
python3 tools/make_print_projects.py --export-dir build/handover-r1/export --output build/handover-r1/single
/Applications/FreeCAD.app/Contents/Resources/bin/python tools/make_colored_projects.py --export-dir build/handover-r1/export --single-color-dir build/handover-r1/single --output build/handover-r1/colored
python3 tools/package_release.py --export-dir build/handover-r1/export --print-dir build/handover-r1/colored --release-id handover-r1 --output build/handover-r1/package
```

导出先强制完整重算和验证，输出42个打印件的两种坐标STL及含硬件的50实体STEP。中间单色排盘和最终涂色项目均保存后独立重开切片。最终使用`colored`的结果；其中本来单色制造的主体、饰片和连接片继续保持单色。

打包检查完整16盘及零件覆盖，将主体与默认文字载板按三类组件路径整理到build候选包。候选包不是已经批准的当前交付；生成器不会写入`printing/`，也不会覆盖个人调整件。可选车型卡槽有各自源文件和验证流程，不混入整机排盘计划。

## 局部生成与确认交付

`make_print_projects.py`可用`--only`选择排盘计划中的盘号；若继续使用`make_colored_projects.py --only`，选择范围必须在中间结果内。局部结果只能作为对应零件的候选，不能通过完整打包检查。

只生成连接片可运行：

```sh
/Applications/FreeCAD.app/Contents/Resources/bin/python tools/make_reinforcement_project.py --output build/reinforcement-r1
```

确认几何、保存后的3MF、重开切片和接口后，再由维护者把选中的文件放到`printing/main/`、`printing/sign-carriers/`或`printing/parking-inserts/`，更新目录说明与`printing/catalog.json`。替换前将旧交付及证据归档，保留原哈希；个人设置文件单独保留并说明适用范围。

常规STL不带颜色；最终3MF保留实际Bambu配色。打印文件不含外购硬件、通用托座样件或零厚度色面；通用底脚试配项目另见卡槽规范。确认打印机、喷嘴和实际装料后重新切片使用，不交付G-code。
