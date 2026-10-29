# 打印项目和发行

当前没有正式整机发行版。[2026-10-29 M Power带色预览](../printing/mpower-color-preview-2026-10-29/README.md)已按当前26个实体生成12盘带Bambu涂色的3MF，并逐盘重开切片通过；总耗材3003.3g、估算128小时41分，按80元/kg材料费240.26元。旧单色预览的1838.7g、34小时48分、147.10元不包含完整配色。
`printing/plate-plan.json`仍为draft，排盘和支撑待实物确认。右半书架已开启支撑，顶部字牌和侧口号板背面贴床、文字面朝上。
常规STL不保留颜色；`make_colored_projects.py`会把CAD逐面颜色和M Power色面映射成Bambu三角涂色，几何不变。上方字与载板已是一体Body，白字通过涂色分配耗材；不另打旧版独立字件。

| 3MF用途 | 位置 |
|---|---|
| 人工持续编辑的排盘和打印设置 | `printing/projects/` |
| 当前12盘带色预览、逐盘统计及来源记录 | `printing/mpower-color-preview-2026-10-29/` |
| 旧单色成本基线压缩包 | `printing/garage-bookshelf-v5-cost-preview-2026-10-28.zip` |
| 自动生成、重开切片验证的结果 | `build/<run-id>/3mf/` |
| 当前独立试件及其原始检查 | `studies/parking-tray-fit-2026-10-26/` |
| 已确认整套交付快照 | `releases/<release-id>/printing/3mf/` |
| 已淘汰的查看模型 | `archive/proposals/` |

## 生成和检查

1. 用FreeCAD Python执行`tools/export.py --output build/export-001`。
2. `python3 tools/make_print_projects.py --export-dir build/export-001 --only 12-side-cartridge`可只生成一盘；省略`--only`生成全计划。
   该工具读取当前验证过的打印STL，保存3MF后重新加载实际切片，不覆盖项目预设；临时G-code留在自动清理的scratch中。
3. 用FreeCAD Python执行`tools/make_colored_projects.py --export-dir <几何导出目录> --single-color-dir <上一步完整打印结果目录>`生成带色项目。它保留原网格，保存三角涂色后重新打开实际切片，并核对每盘使用的色槽；默认新建`build/`目录。
4. 手调项目另存到`printing/projects/`，记录源CAD哈希和修改内容；生成器不会写这个目录。
5. 现有正式打包入口只支持原单材料流程：确认方案及设置后，将计划`status`改为`approved`并完整生成。使用
   `python3 tools/package_release.py --export-dir build/export-001 --print-dir <完整打印结果目录> --release-id <新版编号>`建立快照。

打包检查当前CAD哈希、输出文件哈希、打印结果与导出关联、全零件覆盖和保存项目重开切片状态。
历史报告、部分盘结果、已修改却未重验的文件不能冒充完整发行。已存在release不会覆盖。
若手调或带色3MF准备纳入正式发行，应先扩展/更新发行验证与清单流程，再发行；当前单材料打包入口不接收带色预览。

STL有两种坐标：`stl/assembly/`保持装配位置；`stl/print/`按打印方向旋转并归零。
STEP包含26个打印实体和8个外购硬件；打印STL不包含硬件、托座样件或零厚度外观面。
