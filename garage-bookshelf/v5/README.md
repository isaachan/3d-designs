# garage-bookshelf v5

v5整理v4的最新正式设计，模型几何没有变化。唯一正式文件是
[cad/garage-bookshelf-v5-assembly.FCStd](cad/garage-bookshelf-v5-assembly.FCStd)。
它从v4原样复制；FreeCAD内部对象名、参数表达式和原生外观均保留。

当前：49cm主体、四层2/2/3/3停车位、6.6mm层板、1.6mm托座槽、M3螺钉可换字牌、缩短竖杆、M Power配色。
目录整理和工具检查已完成；[12盘M Power带色3MF](printing/mpower-color-preview-2026-10-29/README.md)已生成并重开切片验证，约3.003kg、128小时41分。
颜色保存在Bambu Studio三角涂色数据内；此前1.839kg、34小时48分的单色估算不包含完整配色。
正式打印发行尚未制作；以[当前状态](PROJECT_STATUS.md)为准。

| 目录 | 内容 |
|---|---|
| `cad/` | 唯一正式CAD、当前零件角色与尺寸检查合同 |
| `src/garage_bookshelf/` | 共用建模、停车布局、外观、渲染和3MF工具库 |
| `tools/` | 主动运行的验证、导出、预览、排盘和打包入口 |
| `assets/` | 冻结字形、带来源哈希的打印预设 |
| `printing/projects/` | 持续手工维护的3MF；不会被生成脚本覆盖 |
| `studies/` | 分析和独立试配，保存证据与重生成输出分开 |
| `build/` | 可再生成结果；`build/tmp/`保存临时切片/解压文件，均忽略 |
| `releases/` | 通过对应版本检查的完整交付快照；当前没有整机发行版 |
| `archive/` | 旧改造入口、旧方案、旧导出、阶段验证与选定快照 |
| `docs/` | 当前设计、装配、打印、配色和维护说明 |

## 常用命令

在本目录运行（也可给脚本绝对路径；工具不依赖当前工作目录）：

```sh
/Applications/FreeCAD.app/Contents/Resources/bin/python tools/validate_cad.py
/Applications/FreeCAD.app/Contents/Resources/bin/python tools/export.py
/Applications/FreeCAD.app/Contents/Resources/bin/python tools/render.py
```

命令会显示新的`build/<run-id>/`输出路径。指定`--output build/<自选空目录>`可固定位置，默认不覆盖已有结果。
在FreeCAD中运行[tools/Preview.FCMacro](tools/Preview.FCMacro)恢复视角和配色，默认不保存正式CAD。

排盘：`python3 tools/make_print_projects.py --export-dir <上一步导出目录> --only 12-side-cartridge`。
带色项目：用FreeCAD Python执行`tools/make_colored_projects.py --export-dir <几何导出目录> --single-color-dir <配套单色打印结果目录>`。
完整流程、GUI保存方法及运行环境见[维护说明](docs/maintenance.md)；3MF用途与发行条件见[打印说明](docs/printing.md)。

完整重建生成器尚未追平当前CAD，因此不提供覆盖主模型的重建命令。
当前设计以正式FCStd为权威；[CHANGELOG.md](CHANGELOG.md)记录设计沿革，[迁移索引](archive/source-index.json)记录v4每个文件的去向和原始哈希。
