# 唯一正式模型

2026-11-02：正式模型增加`ReinforcementPlates`组内四个60×30×3mm矩形连接片；均为全约束原生草图＋Pad，使用`ReinforcementParameters`控制尺寸及高度。两条背部拼缝X=200/345mm，上片Z=200–230mm、下片Z=18–48mm，胶粘面Y=164mm、外表面Y=167mm。原47个Body几何不变；当前51个Body包含42个打印件、8个硬件和1个样件。下文47/38个数为加片前基线。

`garage-bookshelf-v5-assembly.FCStd`为当前设计源。它以v4正式CAD为基线，2026-10-30加入12个独立三色饰片，随后修正为齐平内嵌：仅module_2/module_3开承托槽和胶槽，其余33个Body几何不变。
原始CAD快照保存在`../archive/snapshots/2026-10-30-before-separate-skins.FCStd`，原始SHA256为`822d05f79b60b10a8a9958e427d9591d476a89f391914b90d9eaa1d83fde6958`。

当前共47个Body：38个打印件、8个外购M3硬件和1个托座样件。`model-spec.json`明确列出角色和检查尺寸。

`BookColorSkins`中12个饰片采用原生SubShapeBinder、Extrusion、Common与Body BaseFeature；主体采用原生Offset2D轮廓和PartDesign Pocket，没有Python特征代理或导入网格。名义轮廓固定引用开槽前的Fillet特征，并保留装配位移的参数表达式。`SkinParameters`默认厚0.6mm、承托宽1.5mm、下沉胶槽深0.2mm、侧边间隙0.15mm、转角间隙0.1mm；旧AdhesiveGap保留为0，不再额外垫高。原`MColorParameters`仍控制条带宽度和斜率。
旧书架零厚度色面保留为隐藏构造参考，广告支架的零厚度涂色继续显示。

日常编辑以此FCStd为准。参数变化后重算、保存并运行验证/导出；若有意改变检查尺寸，须同步修改`model-spec.json`。不要运行历史builder覆盖它。

错误的外贴版CAD快照已删除。当前饰片正面恢复原平面；胶放入下沉槽，承托台阶决定高度。
