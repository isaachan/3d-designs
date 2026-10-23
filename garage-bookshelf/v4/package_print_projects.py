"""Write the print guide, manifest and compact delivery ZIP from validated 3MFs."""
import json,zipfile,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent


def package_delivery(report):
    output=ROOT/'bambu-projects'
    colors={'gray':'灰色','yellow':'黄色','black':'黑色','white':'白色','blue':'蓝色'}
    contents=['层板1：双车位，B01轮椅标识','层板2：三车位','层板3：空白整板','车库底背一体模块','书架左模块（含隔板）','书架右模块（含右侧板）',
              '承托柱段 ×12','封顶柱段 ×4','广告牌 ×1＋背面支架 ×2','两行白字，共20个独立字形','两句竖向凹刻口号蓝牌 ×1']
    assert report['status']=='passed' and len(report['projects'])==11
    lines=['# garage-bookshelf v4 · X2D 打印 3MF', '',
           '这套文件对应 v4 CAD：490 mm 主体（200 mm 车库＋290 mm 书架）、48 mm 外挂蓝牌；书架较原版缩短50 mm，两句口号竖向排列；书架底部四处 RootRib 三角肋已移除。', '',
           '共 **11 个 3MF 项目、11 次打印、46 个实体**。每个项目只使用一种颜色，无需 AMS。', '',
           '本次三块停车层板右边缘额外收短4 mm，现为195.6 × 158.6 × 5 mm；左边缘和四孔位置不变。请使用更新后的01a、01b、01c项目。', '',
           '## 打印方法', '',
           '1. 在 Bambu Studio 中以「打开项目」方式打开对应 3MF，保留项目内的打印配置和排盘。',
           '2. 配置按 **X2D、标准 0.4 mm 喷嘴、PLA、纹理 PEI 板**准备；按实际装料选择该盘颜色，确认与机器喷嘴和热床一致，再切片打印。',
           '3. 01a、01b、01c 分别对应双车位层板1、三车位层板2、空白层板3，各打印 **1 次**。其余项目也各打印一次；05、06 盘已摆好全部所需柱段。', '',
           '0.20 mm 层高、4 圈墙、25% 填充、4 mm auto brim。PLA 温度采用官方预设：喷嘴 220°C、纹理 PEI 板 55°C。03 盘启用普通自动支撑、仅从热床生成，其余关闭支撑。', '',
           '| 项目 | 颜色 | 每盘内容 | 打印次数 | 单盘预计时间 | 单盘预计耗材 |',
           '| --- | --- | --- | ---: | ---: | ---: |']
    manifest=[]
    for row,content in zip(report['projects'],contents):
        name=Path(row['project']).name;minutes=round(row['estimated_seconds']/60);hours,minutes=divmod(minutes,60)
        lines.append(f"| [{name}]({name}) | {colors[row['color']]} | {content} | {row['print_runs']} | {hours}小时{minutes}分 | {row['estimated_filament_g']:.1f} g |")
        manifest.append(dict(project=name,color=colors[row['color']],contents=content,print_runs=row['print_runs'],
                             sha256=row['project_sha256'],reopened_and_sliced=True))
    seconds=sum(r['estimated_seconds']*r['print_runs'] for r in report['projects'])
    mass=sum(r['estimated_filament_g']*r['print_runs'] for r in report['projects'])
    lines += ['',f'全套累计切片估算：约 **{seconds/3600:.1f} 小时、{mass/1000:.2f} kg PLA**（每个项目打印一次）。实际耗时和耗材随机器、耗材及校准设置变化。', '',
              '## 装配与颜色', '',
              '白字在08盘单独打印，按字间位置粘在07盘的黑色广告牌上；09盘为蓝色一体件，凹刻口号可在打印后填白漆。',
              '层板1为72×90mm双车位、B01有轮椅图案；层板2为48×90mm三车位；层板3空白。两块带图案层板底面贴床、凹刻朝上。停车线/编号/轮椅及黄线凹刻0.4mm，蓝底凹刻0.2mm，打印后按CAD参考图填色；灰色单耗材3MF不会自动打印白/黄/蓝图案。',
              '09盘凹刻正面朝热床、折边朝上；文字位于首0.6 mm，可查看前3层切片确认。03盘燕尾下方的支撑需清理后再干装。',
              '车库四根立柱均为分段结构：先装最下段四柱，再放层板，继续交替安装上一段柱和下一块板，最后装封顶段。', '',
              '## 验证', '',
              '每个保存后的3MF均被重新加载并实际离线切片；验证时没有另行加载STL，也没有覆盖项目内预设。检查了单盘对象数、无模型切片警告、单一耗材、毫米单位，以及带4mm brim的排盘范围。',
              '完整的X2D启动/结束模板、PLA参数、喷嘴状态及颜色均保存在3MF内。压缩包不含打印G-code，打开项目后可按实际机器重新切片。', '',
              '喷嘴状态采用每个热端各一个标准0.4mm喷嘴的离线配置，各盘使用主喷嘴。尚未进行实物打印。', '']
    if any(Path(row['project']).parent.name!='bambu-projects' for row in report['projects']):
        lines += ['本地 `bambu-projects/` 中另有用户修改过的项目，已原样保留。完整 ZIP 和同名解压目录使用 SHA256 匹配既有验证记录的标准项目；打印完整套件时以完整交付包为准。', '']
    (output/'README.md').write_text('\n'.join(lines))
    (output/'print-manifest.json').write_text(json.dumps(dict(cad_sha256=report['cad_sha256'],projects=manifest,
        print_runs=11,physical_solids=46,estimated_total_hours=seconds/3600,
        estimated_total_filament_g=mass,gcode_included=False),ensure_ascii=False,indent=2))
    archive=ROOT/'garage-bookshelf-v4-X2D-print-3mf.zip'
    validated_sources={Path(row['project']).name:ROOT/row['project'] for row in report['projects']}
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for file in sorted(output.iterdir()):
            if file.suffix in ('.3mf','.png','.md','.json'):
                z.write(validated_sources.get(file.name,file),'garage-bookshelf-v4-X2D-print-3mf/'+file.name)
        for name in ('assembly-preview.png','blue-sign-preview.png','parking-deck-1-preview.png','parking-deck-2-preview.png'):
            z.write(ROOT/'reports'/name,'garage-bookshelf-v4-X2D-print-3mf/previews/'+name)
    delivery=ROOT/'garage-bookshelf-v4-X2D-print-3mf'
    delivery.mkdir(exist_ok=True)
    keep={p.name for p in output.iterdir() if p.suffix in ('.3mf','.png','.md','.json')}
    for p in delivery.iterdir():
        if p.is_file() and p.suffix in ('.3mf','.png','.md','.json') and p.name not in keep:p.unlink()
    for name in keep:
        source=validated_sources.get(name,output/name)
        if source.resolve()!=(delivery/name).resolve():shutil.copy2(source,delivery/name)
    previews=delivery/'previews';previews.mkdir(exist_ok=True)
    for name in ('assembly-preview.png','blue-sign-preview.png','parking-deck-1-preview.png','parking-deck-2-preview.png'):
        shutil.copy2(ROOT/'reports'/name,previews/name)
    print(f'Packaged {archive.name}: {archive.stat().st_size} bytes',flush=True)

if __name__=='__main__':package_delivery(json.loads((ROOT/'slicer-validation.json').read_text()))
