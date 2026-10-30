# garage-bookshelf v5

当前采用**黑色书架主体＋齐平内嵌三色饰片**。正式源文件是[cad/garage-bookshelf-v5-assembly.FCStd](cad/garage-bookshelf-v5-assembly.FCStd)。

[当前完整15盘](printing/current/README.md)包含齐平修正的05、06、13、14、15和原样合并的其他十盘，共38个打印件。正在打印的其他零件无需重印，手动调整过的03盘保留原位置；旧外贴版和重复输出已删除。

两半书架增加0.6mm深承托凹槽，12片0.6mm饰片齐平装入；1.5mm宽承托台阶内另设0.2mm胶槽。05/06采用0.20mm层高、4圈墙、25%填充。先拼好两半书架，再干装和粘接饰片。CAD、几何和重开切片检查见修正包；实物试配、粘接和载荷尚待验证。

仍保留49cm主体、四层2/2/3/3共10槽、6.6mm层板、1.6mm托座槽、M3螺钉可换字牌、缩短竖杆和M Power配色。
[当前状态](PROJECT_STATUS.md) · [装配](docs/assembly.md) · [打印](docs/printing.md) · [维护](docs/maintenance.md)

| 目录 | 内容 |
|---|---|
| `cad/` | 正式CAD及38件尺寸/角色合同 |
| `src/garage_bookshelf/` | 共用原生建模、外观、验证及打印库 |
| `tools/` | 验证、导出、渲染、排盘和打包入口 |
| `assets/` | 冻结字形与打印预设 |
| `printing/projects/` | 人工维护的3MF；生成器不覆盖 |
| `studies/` | 车型、结构与配合试件 |
| `build/` | 可再生成输出与临时切片结果，忽略提交 |
| `printing/current/` | 当前完整15盘、CAD及验证记录 |
| `archive/` | 原始CAD、旧计划及历史记录 |
| `docs/` | 当前设计、装配、打印及配色说明 |

## 常用命令

在本目录运行，也可给脚本和输入绝对路径：

```sh
/Applications/FreeCAD.app/Contents/Resources/bin/python tools/validate_cad.py
/Applications/FreeCAD.app/Contents/Resources/bin/python tools/export.py --output build/<run>/export
python3 tools/make_print_projects.py --export-dir build/<run>/export --output build/<run>/single
/Applications/FreeCAD.app/Contents/Resources/bin/python tools/make_colored_projects.py --export-dir build/<run>/export --single-color-dir build/<run>/single --output build/<run>/colored
/Applications/FreeCAD.app/Contents/Resources/bin/python tools/render.py --output build/<run>/render
```

`<run>`选新的目录名，生成工具不覆盖既有结果。单色项目用于中间验证，最终使用colored结果；其中05/06和13–15仍为单色制造。
在FreeCAD内运行`tools/Preview.FCMacro`恢复原生配色和视角，默认不保存。

完整历史重建器尚未追平当前设计，不用于覆盖主CAD；当前原生CAD可以直接修改参数和重算。
`tools/implement_separate_skins.py`和`tools/implement_flush_inlays.py`是已执行的一次性迁移，普通维护不重复执行。
[CHANGELOG.md](CHANGELOG.md)记录设计沿革。当前只保留一套完整15盘及正在使用的十盘个人文件，旧外贴版和重复试验已删除。
