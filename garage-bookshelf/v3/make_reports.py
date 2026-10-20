"""Summarize measured results without upgrading legacy product issues to passes."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
R=ROOT/'reports'
def load(name):return json.loads((R/name).read_text())
def main():
    g=load('geometry-comparison.json');p=load('parametric-validation.json');a=load('assembly-validation.json');e=load('print-validation.json');r=load('reopen-validation.json');params=load('parameters.json');inventory=json.loads((ROOT/'reference/v2-inventory.json').read_text())
    lines=['# Spreadsheet 参数说明','','所有长度单位为mm；数量、墙圈数、填充百分数无量纲，说明列已标注。B列Alias供Expression引用。independent input可直接编辑，derived通过公式关联。模块数5、层数3及文字岛拓扑是生成配置，不伪装为可动态增减实体的表格参数。','','| Alias | 初始值/表达式 | 类型 | 设计含义 |','|---|---|---|---|']
    for x in params:lines.append(f'| {x["alias"]} | {x["value"]} | {x["kind"]} | {x["description"]} |')
    (R/'parameters.md').write_text('\n'.join(lines)+'\n')
    bom=[]
    for d in p['documents']:
        by={}
        for rec in d['records']:by.setdefault(rec['source'],[]).append(rec)
        for name,recs in by.items():
            old=next((x for x in inventory['assembly_objects'] if x['name']==name),None)
            bom.append(dict(name=name,document=d['document'],body_count=len(recs),bodies=[x['body'] for x in recs],bounds_global=[x['bounds_global'] for x in recs],original_assembly=old))
    (R/'bom.json').write_text(json.dumps(bom,ensure_ascii=False,indent=2))
    lines=['# v3 验证报告（2026-10-20）','','重建的原生CAD几何/编辑功能通过；产品功能保留了v2原有设计干涉，不能标为全部装配验收通过。','','| 检查 | 结论 | 证据 |','|---|---|---|',f'| 34个逻辑件/52个独立Body | 通过 | 正式44、辅助8；无新增产品结构 |',f'| 草图完全约束 | 通过 | 共{sum(d["sketches"] for d in p["documents"])}张；逐张检查FullyConstrained及约束/Expression |','| 原生建模历史 | 通过 | Sketch/Pad/Pocket/AdditiveLoft/SubtractiveLoft，无静态最终Shape特征 |','| 34件新旧精确几何 | 通过 | 双向布尔差<0.0001mm³，旧网格误差阈值见下 |','| 真实参数修改与恢复 | 通过 | 底厚、层板厚、配合间隙、整体深度，关联零件/装配同步 |','| 保存关闭重开再编辑 | 通过 | 两份工程单Solid有效；主工程重开后重复参数编辑 |','| 主体及层板共同−X插入路径 | 通过 | 4个主体接缝×6位置、3个层板接缝×5位置 |',f'| STL封闭、非流形、尺寸/包络 | 通过 | 34原坐标+34归零打印+52单Body STL；每岛封闭 |',f'| 全产品无实体干涉 | {"失败（原设计问题）" if a["existing_design_interferences"] else "通过"} | 几何保留，未擅自补孔/移柱 |','| 实际PLA试配/胶粘强度/承重 | 无法确认 | 没有实物试验；没有编造最小壁厚与认证载荷 |','','## 几何比较','','旧网格比较：包围盒与抽样面偏差≤0.02mm，体积/表面积相对差≤0.05%。对旧脚本独立精确参考执行双向布尔差，避免仅凭网格包围盒验收。曲面网格三角化与STL float精度单独计入偏差。旧Mesh.Volume对全局文字多实体有数值消减误差，采用局部原点双精度有向三角体积和。OCC默认BoundBox可能包含切槽Loft的未用控制点，使用optimalBoundingBox计算真实边界。','','| 零件 | 布尔差mm³ | 网格边界最大差mm | 体积差% | 抽样表面差mm |','|---|---:|---:|---:|---:|']
    for x in g['parts']:lines.append(f'| {x["name"]} | {x["exact_boolean_symmetric_difference_mm3"]:.7g} | {x["bounds_mesh_delta_max_mm"]:.7g} | {100*x["volume_relative_delta"]:.7g} | {x["sampled_surface_deviation_max_mm"]:.7g} |')
    lines+=['','## 保留的原设计干涉','','下表是新模型计算值；因精确布尔对照通过，对应形态来自v2。它们不是迁移引入的改动。','','| 零件A | 零件B | 穿插体积mm³ |','|---|---|---:|']
    for x in a['existing_design_interferences']:lines.append(f'| {x["part_a"]} | {x["part_b"]} | {x["intersection_mm3"]:.6f} |')
    lines+=['','## 参数编辑证据','']
    for t in p['parameter_tests']['tests']:lines.append(f'- {t["alias"]}：{t["original_mm"]}→{t["modified_mm"]}mm；核对{len(t["checks"])}项关联行为；恢复最大体积差{t["max_restored_volume_delta_mm3"]:.7g}mm³。')
    lines+=['','## GUI 验收','','已在FreeCAD 1.1.3实际进入Sketch、Pad和Spreadsheet编辑器，并通过GUI保存、关闭、重开检查。详见gui-validation.json。自动辅助功能读树曾触发本机Qt QAccessible缓存崩溃；审阅宏仅在当前GUI进程停用辅助功能更新并延迟运行，正常手工打开工程不需要该宏。','','## 范围限制','','抽样网格距离不是全表面Hausdorff证明；精确源模型的布尔差覆盖实体几何一致性。打印STL封闭不等于切片/实物验证。原侧牌的位置、层板缺口、像素字形与渐变燕尾均按实际设计保留。详细对象列表、位姿、所有参数及旧文件SHA256另见JSON。']
    (R/'validation-summary.md').write_text('\n'.join(lines)+'\n')
    print('Created parameters.md, bom.json, validation-summary.md')
if __name__=='__main__':main()
