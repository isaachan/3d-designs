# v5迁移说明

本目录3MF和验证保留当时v4源CAD哈希。build_review.py已迁移为读取v5正式CAD，默认重新生成到build/studies/parking-tray-fit/，可用--output指定别的build/子目录；不会覆盖本目录证据。

以下为原研究/试件说明，数值与验证均保留其原始适用版本。

---

# 临时三车位层板＋停车托座

`TEMP-3bay-deck-and-one-parking-tray.3mf`：1盘、2个独立对象，各1件。

- 层板直接取自当前正式CAD的 `garage_deck_2_Body`：301–303三车位，195.6 × 158.6 × 6.6 mm，含三处1.6 mm深浅槽、取放缺口及现有凹刻停车图案。
- 托座取自 `parking_tray_interface_Body`：40 × 80 × 2 mm通用底脚，带取放耳后包络40 × 83 × 3.2 mm。落座后基板高出板面0.4 mm；名义单边间隙0.3 mm。
- 托座仅含通用底脚和取放耳，未包含车型轮胎夹，不能单独固定车轮。
- 3MF内层板与托座分别底面贴床，槽口和取放凸起朝上，自动排在同一盘。
- X2D、0.4 mm、黑色PLA、纹理PEI、0.20 mm层高、4圈墙、25%填充、4 mm自动brim、无支撑。图案为实体凹刻，CAD填色和三色外观面未作为多色耗材导出。
- 保存后已重新加载3MF离线切片：2对象、1盘、无模型警告。估算149分钟、126.0 g；未实物打印。

`seated-preview.png` 显示同一托座落在302号车位的CAD效果；`plate-preview.png` 显示3MF内的实际打印排盘。装配预览将托座临时显示为橙色以便辨认，3MF使用单一黑色PLA。

正式CAD及既有打印文件未修改。源文件与输出哈希、网格检查、三个槽的落座与抬出路径见 `validation.json`。

复现：`/Applications/FreeCAD.app/Contents/Resources/bin/python build_review.py`
