# 阶段二：原生参数化架构

- DesignParameters：所有结构尺寸、位置、制造间隙分行，B列带Alias及mm单位；独立输入和派生表达式分开。整体宽度由五段宽之和派生，层高、接口位置及装配平移均通过Expression更新。零件个数为拓扑参数：更改数量需改配置重建，不能宣称改一个单元格能新增Body。
- 主工程4个App::Part成品分类，子零件App::Part负责全局Placement；Body内部几何是局部坐标。44个Body，没有链接实例；每个都有独立历史，但共用表格参数。
- 主体：底板Sketch+Pad，背板Sketch+Pad；模块2/5竖板Pad及三角肋Pad；公榫成对截面Sketch+AdditiveLoft，母槽Sketch+SubtractiveLoft。Loft是原设计的必要变截面特征，不能用直Pad/Pocket替换。
- 层板：矩形Sketch+Pad→缺口Sketch+Pocket→双公榫AdditiveLoft或双母槽SubtractiveLoft。缺口不镜像、不补孔。
- 承托柱：圆Sketch+Pad轴→每层两圆截面AdditiveLoft锥肩→圆Sketch+Pad托环。
- 支架、加强片、侧牌：矩形Sketch+Pad。文字：源掩码通过临时等厚棱柱并集提取精确平面轮廓，仅作轮廓计算辅助，逐个实体建立含内孔闭环的Sketch+Pad；不把辅助Shape存入最终对象，也不采用Shape赋值。
- 试件及缩短件：独立auxiliary.FCStd，8个Body；正式装配不混入试件。
- geometry/sketches.py负责尺寸约束及Expression；features.py负责原生特征与逐步有效性；components负责各类几何；assembly.py只处理装配关系；validation.py负责一致性、重算、参数变化、保存重开及干涉检查；export.py负责STL及网格/尺寸检查；main.py负责分阶段构建。
- 全约束策略：闭环各线端点Coincident，每个顶点X/Y尺寸通过Expression引用表格（0也为真实坐标尺寸）；圆具有圆心X/Y与半径约束。无需Block/固定几何，避免依赖鼠标拖动和面编号绑定。
- 验证：单Solid/Shape.isValid、全部Sketch.FullyConstrained、各对象State、依赖图无环、关键表达式数量；真实修改BaseThickness并核对五模块及柱下端同步，再改DeckThickness核对六层板，恢复；独立重开FCStd再次验证。
- 比较分为精确参考与旧网格：界限分别1e−5mm与0.02mm，体积/面积相对网格容差0.05%；精确实体做双向布尔体积差，网格顶点到新表面抽样距离；圆柱STL的弦高误差明确标注。所有34个原STL均有映射和比较。
- 单件STL按原STL坐标系保留（4柱的原STL相同）；另外打印目录归零摆放，变换单独记录。导出不是修改工程内装配。网格只在最终导出及旧模型校验中使用。
