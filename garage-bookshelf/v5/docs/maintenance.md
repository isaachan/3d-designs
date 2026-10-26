# 维护和运行

CAD检查、导出、渲染和原生试件使用FreeCAD自带Python（本机路径`/Applications/FreeCAD.app/Contents/Resources/bin/python`）。
它配套的`lib/`由tools入口自动定位；不要用系统Python安装FreeCAD。软件渲染需要该环境的NumPy和Pillow。
打印排盘/打包工具可用Python 3.11+，排盘需要安装Bambu Studio；使用`assets/print-profiles/`已冻结的预设，不会刷新或覆写预设源。

所有tools支持`--help`；路径可从任意工作目录调用。生成工具默认创建新的`build/<run-id>/`，或显式传`--output build/<空目录>`。
`validate_cad.py`只读CAD；`export.py`先验证、再导出；`render.py`只读CAD材质并写预览。

FreeCAD GUI中运行`tools/Preview.FCMacro`，或在Python控制台：

```python
from pathlib import Path
import sys
# project改成你选择的v5目录；宏会自动定位，无需手写这两行
project = Path('/path/to/garage-bookshelf/v5')
sys.path.insert(0, str(project / 'src'))
from garage_bookshelf.appearance.view import review
review()            # 只恢复内存中的显示和视角
# review(save=True) # 明确需要时才保存正式CAD
```

参数编辑后重算、检查并保存正式CAD，再运行验证/导出。新的CAD哈希会让旧生成结果无法直接复用。
若新增/删除实际零件或有意修改检查尺寸，同步更新`cad/model-spec.json`。
`src/`中的原生几何辅助可供后续增量使用；旧完整builder未覆盖全部设计改造，已归档且禁止直接执行。

历史研究和试件各带说明。试件重生成写入`build/studies/`，不覆盖`studies/`内保存的3MF、CAD、网格与证据。
`build/tmp/`用于临时切片状态、G-code和解压；可在工具退出后清理。手工修改3MF必须另存到`printing/projects/`。
