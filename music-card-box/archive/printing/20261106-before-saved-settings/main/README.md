# 主体 r1

[深蓝主体 3MF](01-darkblue.3mf) · [主体 STL](evidence/CassetteShell.stl) · [验证记录](validation.json) · [原生 CAD](../../../cad/music-card-box-r1.FCStd)

主体 190.4 × 38.4 × 92 mm；底面放在热床，开口向上。**3MF 已写入“仅外侧 brim，宽度 5 mm”**，以 Bambu Studio 项目方式打开即可载入设置。沿用 garage-bookshelf 的 X2D / 标准 0.4 mm / PLA / 纹理 PEI 配置；层高 0.20、4 道墙、15% 填充、5 层顶底、无支撑。装饰选用 [cassette-r1](../../decorations/cassette-r1/README.md)。

适用于用户提供的 180 × 101 mm 卡片与约 20 mm 整摞厚度，有效槽宽 / 厚度 184 / 25 mm。卡片净空、实体有效性、CAD 保存重开、分件干涉、贴胶平面及网格封闭检查已通过；原始证据随 `evidence/` 保存。装卡效果图的卡片张数与谱面仅作示意。

已用 Bambu Studio 重新打开确认设置保留，并完成主体切片，G-code 中实际生成 Brim 路径；[切片结果](slice-result.json)和[扩边验证](evidence/brim-5mm/brim-check.json)随当前文件保存。交付的 3MF 是可编辑项目，不含 G-code。原始几何版已完整[归档](../../../archive/printing/20261104-before-brim-5mm/README.md)。

CLI 日志包含本机缺少 `machine_full/process_full` 预设路径、颜色索引和官方 X2D 特殊 T 指令的时间分析警告，见[原始切片日志](evidence/brim-5mm/slice-check.log)；切片退出成功，模型未报告警告。尚未实物打印、取放或上墙承载测试。

不同角度：[正面](views/front.png) · [另一侧斜视](views/opposite.png) · [空盒俯视](views/top.png) · [背面贴胶示意](rear.png)。新增视角仅改变相机，记录见 [views.json](views/views.json)。
