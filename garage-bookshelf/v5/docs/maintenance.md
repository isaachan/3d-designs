# 维护和运行

CAD检查、导出、渲染和原生试件使用FreeCAD自带Python（本机路径`/Applications/FreeCAD.app/Contents/Resources/bin/python`）。
它配套的`lib/`由tools入口自动定位；不要用系统Python安装FreeCAD。软件渲染需要该环境的NumPy和Pillow。
打印排盘/打包工具可用Python 3.11+，排盘需要安装Bambu Studio；使用`assets/print-profiles/`已冻结的预设，不会刷新或覆写预设源。

常规生成工具支持`--help`，一次性迁移和专项修正打包脚本按其文档执行；路径可从任意工作目录调用。生成工具默认创建新的`build/<run-id>/`，或显式传`--output build/<空目录>`。
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
若新增/删除实际零件或有意修改检查尺寸，同步更新`cad/model-spec.json`。饰片厚度/承托宽度/胶槽深度/侧边及转角间隙在`SkinParameters`，条带宽度和斜率继续使用`MColorParameters`；原生特征会自动重算。
`src/`中的原生几何辅助可供后续增量使用；旧完整builder未覆盖全部设计改造，已归档且禁止直接执行。

历史研究和试件各带说明。试件重生成写入`build/studies/`，不覆盖`studies/`内保存的3MF、CAD、网格与证据。
`build/tmp/`用于临时切片状态、G-code和解压；可在工具退出后清理。手工修改3MF必须另存到`printing/projects/`。

当前完整流程为导出→15盘单色中间检查→CAD涂色→重开切片→完整快照，见`docs/printing.md`。`implement_separate_skins.py`为已完成的一次性迁移，普通维护不重复运行。

`implement_flush_inlays.py`为外贴版到齐平内嵌版的一次性迁移。名义表面引用原始Fillet特征并复制装配位移的参数表达式，避免开槽后的主体反向依赖轮廓。验证必须强制完整重算，以发现循环引用。当前发布已合并完整15盘，旧外贴版打包脚本和试验输入已删除。日常按完整导出、排盘、涂色和`package_release.py`流程生成新版本，不重跑一次性迁移。

打印交付统一写入`printing/`；当前15盘固定入口为`printing/current/3mf/`。`package_release.py --release-id <id>`的新版本写入`printing/<id>/`，不再创建releases目录。
