# 打印项目和发行

当前没有完整整机发行版。`printing/plate-plan.json`按当前26个实体列出12盘单材料草案，尚待确认支撑、排盘及配色制造方式。
当前M Power色面不会自动变成多材料3MF。上方字与载板已是一体Body，不能照旧11盘另打独立白字。

| 3MF用途 | 位置 |
|---|---|
| 人工持续编辑的排盘和打印设置 | `printing/projects/` |
| 自动生成、重开切片验证的结果 | `build/<run-id>/3mf/` |
| 当前独立试件及其原始检查 | `studies/parking-tray-fit-2026-10-26/` |
| 已确认整套交付快照 | `releases/<release-id>/printing/3mf/` |
| 已淘汰的查看模型 | `archive/proposals/` |

## 生成和检查

1. 用FreeCAD Python执行`tools/export.py --output build/export-001`。
2. `python3 tools/make_print_projects.py --export-dir build/export-001 --only 12-side-cartridge`可只生成一盘；省略`--only`生成全计划。
   该工具读取当前验证过的打印STL，保存3MF后重新加载实际切片，不覆盖项目预设；临时G-code留在自动清理的scratch中。
3. 手调项目另存到`printing/projects/`，记录源CAD哈希和修改内容；生成器不会写这个目录。
4. 确认全套单材料方案及设置后，将计划`status`改为`approved`并完整生成。使用
   `python3 tools/package_release.py --export-dir build/export-001 --print-dir <完整打印结果目录> --release-id <新版编号>`建立快照。

打包检查当前CAD哈希、输出文件哈希、打印结果与导出关联、全零件覆盖和保存项目重开切片状态。
历史报告、部分盘结果、已修改却未重验的文件不能冒充完整发行。已存在release不会覆盖。
若手调3MF准备纳入发行，应先扩展/更新项目验证与清单流程，再发行；当前打包入口只接收本工具生成并验证的完整计划。

STL有两种坐标：`stl/assembly/`保持装配位置；`stl/print/`按打印方向旋转并归零。
STEP包含26个打印实体和8个外购硬件；打印STL不包含硬件、托座样件或零厚度外观面。
