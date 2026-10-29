本目录保存生成脚本和已验证的原始预览快照。重新生成写入 `build/`，不会覆盖本目录文件。

调整过打印参数的手工维护 3MF 另存于 `../../printing/projects/enchery-1-65-mazda-mx5-parking-tray-preview.3mf`，其实际设置与验证见同名说明。

# ENCHERY 1:65 Mazda MX-5 停车托座预览

`enchery-1-65-mazda-mx5-parking-tray-preview.3mf`：仅一个托座、一个对象、一盘，无层板和车模。

- 车模理论尺寸由用户给定：61.2 × 27.1 × 19.3 mm。
- 沿用正式 CAD 的 40 × 80 × 2 mm 圆角底脚及取放耳；总包络 40 × 83 × 3.4 mm。
- 两侧低挡高 1.4 mm，内净宽 29.1 mm；八个斜面轮挡高 1.2 mm。
- 轴距 36 mm、轮距 23 mm、轮胎直径 9 mm、宽 3 mm 均为视觉预览估算；轮挡宽松放置，未设计弹性卡扣，未实测夹持效果。
- `top-fit-preview.png` 中蓝色虚线是车模的理论长宽，灰色轮胎仅用于说明估算位置，均未放入 3MF。
- FreeCAD 文件保留原始底脚，并使用全约束草图和原生 Pad 添加侧挡与轮挡。`VehiclePreview` 中可编辑预览参数；原始底脚为正式 CAD 的形状快照。
- X2D、0.4 mm、黑色 PLA、0.20 mm 层高、4 圈墙、25% 填充、4 mm 自动 brim、无支撑。
- 已重开 CAD 并重算，检查封闭单连通网格、十个正式车位无干涉；已重新加载 3MF 切片，无模型警告。估算 16 分钟、7.6 g；未实物打印。
- 正式 CAD 哈希保持不变。详见 `validation.json`。

复现：用 FreeCAD Python 运行 `studies/enchery-mx5-tray-2026-10-29/build_preview.py --output build/<新目录>`。
