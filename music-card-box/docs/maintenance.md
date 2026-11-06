# 维护与复现

所有命令在 `music-card-box/` 运行。本项目不导入、保存或改写 `garage-bookshelf/` 的模型与工具。

## 源文件

正式可编辑源文件见[CAD 索引](../cad/README.md)。原生总装含 Spreadsheet 尺寸、全约束草图、Pad、Pocket 与 Fillet，未使用导入网格作为 CAD。装饰圆的定位使用固定几何约束，功能轮廓采用尺寸表达式。

`assets/design.json` 是生成输入。功能尺寸、配色和关联布局需要同步变更时，修改该文件并在新运行目录重建；部分草图位置和装饰布局在生成时计算，不能假定仅改 FreeCAD 表格便会自动更新所有关联位置。直接编辑正式 CAD 后必须重新验证，并同步输入或明确记录差异。

## 运行

本机环境为 FreeCAD 自带 Python 与 Blender。生成只接受尚不存在的 `build/<运行名>/`，不会覆盖 CAD、旧交付或既有候选结果。

```sh
QT_QPA_PLATFORM=offscreen /Applications/FreeCAD.app/Contents/Resources/bin/python tools/build.py --output build/my-new-run > build/my-new-run.log 2>&1
/Applications/Blender.app/Contents/MacOS/Blender --background --python tools/render.py -- --scene build/my-new-run/scene.json --view hero > build/my-new-run/hero-render.log 2>&1
/Applications/Blender.app/Contents/MacOS/Blender --background --python tools/render.py -- --scene build/my-new-run/scene.json --view empty > build/my-new-run/empty-render.log 2>&1
/Applications/Blender.app/Contents/MacOS/Blender --background --python tools/render.py -- --scene build/my-new-run/scene.json --view rear > build/my-new-run/rear-render.log 2>&1
/Applications/FreeCAD.app/Contents/Resources/bin/python tools/dimensions.py --output build/my-new-run/dimensions.png
python3 -m unittest discover -s tests -v
python3 tools/verify.py
```

生成使用 offscreen 原生视图保存颜色，关闭窗口更新以避免无 OpenGL 的离屏绘制；macOS 可能报告缺少 3Dconnexion 设备库，此警告不涉及实体几何。退出前文件同步保存并重开验证，不执行 Qt/Coin 的退出清理。

增加角度时可读取上述渲染保存的 `hero.blend`（装卡）或 `empty.blend`（空盒），用 `tools/render_angles.py` 仅移动相机，例如：

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --python tools/render_angles.py -- --input build/my-new-run/hero.blend --angle front --output build/my-new-views/front.png
```

角度支持 `front`、`opposite`、`top`；俯视建议输入空盒场景。新增预览在新 build 运行中生成，确认后保存到主体款式的 `views/`，保留场景与工具哈希、原始日志并更新清单，不改变原有几何验证日期。

## 保留当前交付

确认几何与预览后，使用 `python3 tools/release.py --candidate build/my-new-run --log build/my-new-run.log` 将新项目初次交付整理到 `cad/` 与 `printing/`。工具先以 Bambu Studio 的 `--info` 检查四个分色 3MF 可读且为 manifold，不执行切片；已有带结果的导入证据可保留。该工具拒绝覆盖已有正式文件；后续修订须先完整归档被替换交付，再更新修订号和组件索引。原始日志、输入快照与生成工具快照随组件放入 `evidence/`。

按[验证状态](../PROJECT_STATUS.md)区分 CAD 检查、网格检查、切片与实物反馈。没有打印机信息时仅交付通用 3MF；不得用空的切片结果文件冒充通过。变更更新 `CHANGELOG.md`、组件索引、哈希清单和必要的状态说明。

## 主体外侧 brim 项目

主体现已按用户要求保存 5 mm 外侧 brim，使用本项目 `assets/print-profiles/` 内冻结的 X2D 配置，不再依赖其他项目运行时读取。复现候选项目：

```sh
python3 tools/set_main_brim.py --output build/new-brim-project
```

工具通过 Bambu Studio 导出并重开保存，使项目既保留打印设置，又正确登记热床实例。正式更新前比较变换后的网格、原方向与尺寸；先归档旧交付，再更新主体验证、组件清单和装饰记录中引用的旧主体位置。几何验证日期保留原值，打印设置验证日期单独登记。切片 G-code 留在 build 中检查，不混入当前可编辑交付项目。

## 装饰统一排盘

`tools/build.py` 产生基础几何导出。当前装饰打印交付还必须使用冻结的正式总装三角网格 `printing/main/r1/evidence/scene.json` 和 `assets/print-layout.json` 完成排盘及 Bambu 项目转换：

```sh
python3 tools/repack_decorations.py --output build/new-decoration-layout
```

工具保留零件形状，重新将实际胶面置于 Z=0，按固定位置导出三色独立项目，并执行重开、逐盘切片及全部六件同盘的单耗材几何/brim 回归。配色来自冻结场景。确认结果后先归档旧组件，再更新三份 3MF、排盘证据、切片结果、关联验证位置和清单。该流程不验证 AMS 换色。
