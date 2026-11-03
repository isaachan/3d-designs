# garage-bookshelf v5

当前采用**黑色书架主体＋齐平内嵌三色饰片**。正式源文件是[cad/garage-bookshelf-v5-assembly.FCStd](cad/garage-bookshelf-v5-assembly.FCStd)。

当前打印文件：[主体及饰片15盘](printing/current/README.md)＋[连接片补充盘](printing/reinforcement-2026-11-02/README.md)。

[当前状态](PROJECT_STATUS.md) · [装配](docs/assembly.md) · [打印](docs/printing.md) · [维护](docs/maintenance.md) · [变更记录](CHANGELOG.md)

目录结构与文件用途统一遵循[项目总览中的版本目录规约](../README.md#版本目录规约从v5开始)。

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
