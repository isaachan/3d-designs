# garage-bookshelf v3：原生参数化重建

v3 按 v2 已保存装配与源脚本的真实几何重新建模；原目录不修改。主工程保留 26 个原命名逻辑件，拆为 44 个独立实体 Body（包括20个分离文字岛）。辅助工程保留6个接口试件和2个缩短外观验证件；缩短件查看位置沿用原独立工程（模块5另移+135mm），单件STL仍保留原坐标。所有最终实体由原生 Sketcher/Part Design 历史生成，没有 Mesh::Feature、静态 Shape 特征或网格转换体。

## 交付入口

- `garage-bookshelf-v3-assembly.FCStd`：正式装配，4个原分类App::Part，44个Body。
- `garage-bookshelf-v3-auxiliary.FCStd`：8个接口/缩短试件Body。缩短件不可装配或承重；试件在原坐标，彼此可能重叠显示，请按组切换可见性。
- `representative.FCStd`：第三阶段验证的右层板，6张完全约束草图、Pad、Pocket及两个SubtractiveLoft。
- `stl/`：34个与v2同名且坐标系一致的STL；文字每行含10个封闭岛，适合一次排版、逐字粘贴。
- `body-stl/`：52个单Body封闭STL，文字的20个分离字形均能单独打印；坐标沿用对应原STL坐标。
- `print-stl/`：相同34件的打印朝向及归零版本；广告牌与文字放平；其他保留原打印方向。4mm brim内的X2D256×256×260包络自动检查。它们是STL，不是已切片的3MF/G-code。
- `reports/01-design-analysis.md`：设计解析、BOM、接口精确尺寸及冲突清单；机器可读BOM/装配变换见`reference/v2-inventory.json`与`reports/bom.json`。
- `reports/02-modeling-architecture.md`：Body/特征/参数/模块设计及验证策略。
- `reports/parameters.json`、`reports/parameters.md`：参数Alias、输入/派生关系与单位。
- `reports/geometry-comparison.json`：全部34件的精确布尔差、新旧包络、体积、表面积和网格表面抽样偏差。
- `reports/parametric-validation.json`：原生对象类型、每张草图约束、单Solid、无循环、真实参数修改/恢复。
- `reports/reopen-validation.json`：保存、关闭、重开后重算与参数修改测试。
- `reports/assembly-validation.json`：共同−X插入路径及原设计保留的实体干涉。
- `reports/print-validation.json`：STL封闭、连通组件、非流形、单位和打印包络。
- `reports/validation-summary.md`：验证结论、通过/失败/无法确认的集中说明。

## 在 FreeCAD GUI 中编辑

使用本机 FreeCAD 1.1.3 打开主工程，展开分类→零件App::Part→Body，即可看到Sketch、Pad、Pocket、AdditiveLoft/SubtractiveLoft。双击草图进入Sketcher；每个顶点的位置都有尺寸约束，不使用固定几何。零值位置也是显式的约束和表达式。圆具有圆心位置及半径约束。

双击DesignParameters表，编辑B列标为`input`的单元格，例如BaseThickness、DeckThickness、FitClearance、OverallDepth，然后执行“编辑→刷新/重算”（或本机⌘R）。共用参数会更新相关所有Body，装配位置通过表达式随动。`derived`行是公式，优先修改其上游输入；OverallWidth为五模块宽度之和。每行Alias与C/D列说明均保存在工程内。

双击Pad可查看长度；带表达式的数值由表驱动，可在属性表达式编辑器查看`DesignParameters.*`。如确需仅修改某个零件，可给对应Body的特征或草图约束解除该表达式并输入独立值；这会有意取消全局联动。所有Body没有App::Link共享实例。

参数化提供在当前拓扑内的尺寸编辑，不保证任意极端输入仍有有效实体。模块/层板/文字岛数量是Python生成拓扑；改变数量需修改构建配置并重建。局部轮廓没有绑定易变化的面序号，不依赖外部Python代理或运行脚本才能重新计算。修改工程后保存、关闭和重开仍可编辑。

单件导出：选中所需Body→文件→导出→STL，FreeCAD的STL单位按mm。若要保留原零件坐标或统一打印归零位置，使用下述导出脚本。文字可按岛单独导出，也可选中一行的10个Body一起导出。

## 可复现运行（macOS，本机已验证）

```sh
cd /Users/kai.han/code/3d-designs/garage-bookshelf/v3
/Applications/FreeCAD.app/Contents/Resources/bin/python analyze_reference.py
/Applications/FreeCAD.app/Contents/Resources/bin/python verify_reference.py
/Applications/FreeCAD.app/Contents/Resources/bin/python representative.py
/Applications/FreeCAD.app/Contents/Resources/bin/python main.py
/Applications/FreeCAD.app/Contents/Resources/bin/python make_reports.py
```

脚本使用FreeCAD随附Python，开头显式加入本机FreeCAD库路径；其他安装位置可修改该路径或通过已加载FreeCAD的Python环境执行。不要使用没有FreeCAD依赖的普通系统Python。也可用`freecadcmd`执行入口脚本。重新生成会替换v3同名文档/输出文件，不会修改v2。`main.py`要求设计交叉验证与代表件关卡通过，任意建模/检查失败均抛异常并停止。日志可重定向到`reports/build.log`。

`verify_reference.py`只在审计阶段读取旧脚本函数作为独立精确参考；禁止执行其批量导出入口。新零件由components/与geometry/独立生成。文字掩码已冻结在`reference/text-masks.json`，重建无需Swift或字体；`reference_shapes.py`的freeze_masks仅供审计人员重新采样原Swift设计，不是日常重建步骤。

只重新导出已编辑的工程（不重建或改写FCStd）：

```sh
/Applications/FreeCAD.app/Contents/Resources/bin/python export.py garage-bookshelf-v3-assembly.FCStd garage-bookshelf-v3-auxiliary.FCStd
```

STL输出有原坐标及归零打印两套；变换、朝向、尺寸记录在print-validation.json。原PLA墙数4、填充25%、brim4mm作为打印说明保留，STL本身不能储存这些切片参数。v3没有把旧3MF网格重新包装为新CAD，也没有自动提交切片或打印作业。

## 源代码职责

`parameters.py`集中参数及表达式；`geometry/sketches.py`完全约束草图；`geometry/features.py`原生特征/逐步有效性；`components/`区分主体、层板、立柱、燕尾、外观件与试件；`assembly.py`局部/全局变换；`build.py`装配及辅助件编排；`validation.py`几何/依赖/参数/装配验证；`export.py`导出；`main.py`执行阶段关卡；`gui_review.py`在GUI中保存可见性、原配色和视图；`analyze_reference.py`、`reference_shapes.py`、`verify_reference.py`为独立只读审计；`make_reports.py`生成易读报告。

## 保留的原设计问题

旧说明的“层板圆孔”实际不存在；脚本和已保存模型只有边缘矩形缺口。旧说明的“恒定截面燕尾”实际是变截面Loft。v3忠实保留真实几何，未补孔、重定位柱或侧牌。原设计的实体干涉会在装配报告单独标为失败，不能将“重建几何一致”理解为产品已具备可直接组装的功能认证。

PLA实际间隙、最小承重壁厚、支撑清理、胶粘强度及5kg/8辆车承重均无法从现有设计材料确认。本次交付不增加未经批准的结构或尺寸；先依据报告处理原设计问题，再进行实际试配及承载验证。

GUI外观可重建：在FreeCAD Python控制台执行`import sys; sys.path.insert(0, "/Users/kai.han/code/3d-designs/garage-bookshelf/v3"); import gui_review; doc = gui_review.open_model()`，可为重新由无GUI运行生成的工程保存原配色及干净的特征可见性。该脚本只改变视图属性。

自动GUI验收见`reports/gui-validation.json`：已实际进入Sketch、Pad和Spreadsheet编辑器并保存重开。审阅宏为本机Qt/macOS的QAccessible缓存崩溃提供仅当前进程的辅助功能更新绕行，未改变用户配置；正常打开FCStd不需要宏。`Zero`是坐标基准，请保持0mm。

最终复核：运行`verify_delivery.py`可对GUI保存的两份交付文件再次执行原生特征与新旧精确几何检查，并重导出/验证52个单Body STL；运行`make_reports.py`更新易读报告，再运行`final_integrity.py`确认旧目录SHA256和交付完整性。
