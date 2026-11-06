# 主体 r1

[深蓝主体 3MF](01-darkblue.3mf) · [主体 STL](evidence/CassetteShell.stl) · [验证记录](validation.json) · [原生 CAD](../../../cad/music-card-box-r1.FCStd)

主体 190.4 × 38.4 × 92 mm；底面放在热床，开口向上。当前文件保留后续 Bambu Studio 保存设置：**自动 brim、宽度 5 mm**，X2D / 标准 0.4 mm / PLA / 纹理 PEI，层高 0.20、2 道墙、15% 填充、5 层顶部、3 层底部、无支撑、擦料塔开关启用。2026-11-06 已按当前文件重新切片，详见[当前保存设置与结果](../../saved-projects-20261106.json)。装饰选用 [cassette-r1](../../decorations/cassette-r1/README.md)。

适用于用户提供的 180 × 101 mm 卡片与约 20 mm 整摞厚度，有效槽宽 / 厚度 184 / 25 mm。卡片净空、实体有效性、CAD 保存重开、分件干涉、贴胶平面及网格封闭检查已通过；原始证据随 `evidence/` 保存。装卡效果图的卡片张数与谱面仅作示意。

初始“仅外侧 5 mm / 4 道墙”项目的[切片结果](slice-result.json)和[扩边验证](evidence/brim-5mm/brim-check.json)保留原记录，其[原验证输入](../../../archive/printing/20261106-before-saved-settings/README.md)单独归档。当前后续保存项目已重新切片通过，零件形状和直立方向未变，主体在独立热床上平移；与装饰合盘时需要重新排盘。交付 3MF 不含 G-code。更早的几何版也已完整[归档](../../../archive/printing/20261104-before-brim-5mm/README.md)。

CLI 日志包含本机缺少 `machine_full/process_full` 预设路径、颜色索引和官方 X2D 特殊 T 指令的时间分析警告，见[原始切片日志](evidence/brim-5mm/slice-check.log)；切片退出成功，模型未报告警告。尚未实物打印、取放或上墙承载测试。

不同角度：[正面](views/front.png) · [另一侧斜视](views/opposite.png) · [空盒俯视](views/top.png) · [背面贴胶示意](rear.png)。新增视角仅改变相机，记录见 [views.json](views/views.json)。
