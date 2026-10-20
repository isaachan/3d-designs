"""Millimetre design inputs transcribed from v2; derived values stay expressions."""
import json
from pathlib import Path
# alias, value (mm, or = derived expression), purpose
PARAMETERS = [
('Zero','0 mm','局部坐标基准'),
('ModuleWidth1','180 mm','模块1宽'),('ModuleWidth2','230 mm','模块2宽'),('ModuleWidth3','180 mm','模块3宽'),('ModuleWidth4','180 mm','模块4宽'),('ModuleWidth5','150 mm','模块5宽'),
('ModuleStart1','=Zero','模块1位置'),('ModuleStart2','=ModuleWidth1','模块2位置'),('ModuleStart3','=ModuleStart2+ModuleWidth2','模块3位置'),('ModuleStart4','=ModuleStart3+ModuleWidth3','模块4位置'),('ModuleStart5','=ModuleStart4+ModuleWidth4','模块5位置'),('OverallWidth','=ModuleStart5+ModuleWidth5','主体宽（派生）'),
('OverallDepth','220 mm','主体深'),('OverallHeight','238 mm','主体高'),('BaseThickness','8 mm','底板厚'),('BackThickness','5 mm','背板厚'),('WallThickness','6 mm','竖板厚'),('Overlap','0.2 mm','源设计融合重叠/榫根偏移'),('WallStart','=BaseThickness-Overlap','背/竖板起点'),('WallPadLength','=OverallHeight-WallStart','背/竖板高'),('BackFront','=OverallDepth-BackThickness','背板前沿'),
('DividerX','360 mm','中隔板全局X'),('RightWallX','=OverallWidth-WallThickness','右侧板X'),('PanelDepth','=BackFront','竖板深'),('RibSize','25 mm','根肋直角边'),('RibThickness','5 mm','肋厚'),('RibFrontY','12 mm','前肋Y'),('RibRearY','183 mm','后肋Y'),
('TongueLength','14 mm','主体公榫Loft长'),('SocketDepth','15 mm','主体母槽Loft长'),('FitClearance','0.40 mm','名义总侧隙'),('HalfClearance','=FitClearance/2','单侧扩张'),('SocketOvercut','0.2 mm','母槽上下越界'),('BaseJointY1','52 mm','底榫1中心'),('BaseJointY2','168 mm','底榫2中心'),('BackJointZ1','66 mm','背榫1中心'),('BackJointZ2','180 mm','背榫2中心'),
('BaseRootBottom','15 mm','底榫根底半宽'),('BaseRootTop','12 mm','底榫根顶半宽'),('BaseTipBottom','12 mm','底榫末底半宽'),('BaseTipTop','9 mm','底榫末顶半宽'),('BackFrontOverlap','0.2 mm','背榫前沿融合'),('BackRootFront','13 mm','背榫根前半高'),('BackRootRear','17 mm','背榫根后半高'),('BackTipFront','10 mm','背榫末前半高'),('BackTipRear','14 mm','背榫末后半高'),
('DeckHalfWidth','180 mm','层板半片宽'),('DeckWidth','=2*DeckHalfWidth','整层宽'),('DeckDepth','215 mm','层板深'),('DeckThickness','5 mm','层板厚'),('DeckFirstZ','66 mm','首层底高'),('DeckPitch','63 mm','层距'),('DeckZ1','=DeckFirstZ','层1位置'),('DeckZ2','=DeckFirstZ+DeckPitch','层2位置'),('DeckZ3','=DeckFirstZ+2*DeckPitch','层3位置'),('DeckNotchX','153 mm','每半片缺口起X'),('DeckNotchWidth','14 mm','缺口宽'),('DeckFrontNotchDepth','17 mm','前缺口深'),('DeckRearNotchStart','188 mm','后缺口起Y'),('DeckTongueLength','10 mm','层板公榫长'),('DeckSocketDepth','10.2 mm','层板母槽长'),('DeckJointY1','55 mm','层板榫1'),('DeckJointY2','160 mm','层板榫2'),('DeckRootBottom','11 mm','层板根底半宽'),('DeckRootTop','8 mm','层板根顶半宽'),('DeckTipBottom','8 mm','层板末底半宽'),('DeckTipTop','6 mm','层板末顶半宽'),
('DeckBridgeWidth','48 mm','层板跨缝片宽'),('DeckBridgeDepth','110 mm','层板跨缝片深'),('DeckBridgeThickness','3 mm','层板跨缝片厚'),('DeckBridgeX','=DeckHalfWidth-DeckBridgeWidth/2','跨缝片位置'),('DeckBridgeY','55 mm','跨缝片Y'),
('ColumnRadius','6 mm','柱轴半径'),('CollarRadius','14 mm','托环半径'),('ColumnCentreOffset','10 mm','原柱局部轴心'),('ColumnPitchX','330 mm','柱X定位距'),('ColumnPitchY','185 mm','柱Y定位距'),('ColumnTop','230 mm','柱顶Z'),('ColumnHeight','=ColumnTop-BaseThickness','柱轴高'),('ConeHeight','8 mm','锥肩高'),('CollarThickness','4 mm','托环厚'),
('SignWidth','36 mm','侧牌局部宽'),('SignHeight','180 mm','侧牌局部长'),('SignThickness','6 mm','侧牌厚'),('SignBaseZ','50 mm','侧牌装配Z'),
('BillboardHalfWidth','180 mm','广告牌半宽'),('BillboardHeight','64 mm','广告牌高'),('BillboardThickness','6 mm','广告牌厚'),('BillboardBottom','300 mm','广告牌底Z'),('BillboardBridgeWidth','50 mm','广告牌跨缝片宽'),('BillboardBridgeThickness','3 mm','广告牌跨缝片厚'),('BillboardBridgeHeight','36 mm','广告牌跨缝片高'),('BillboardBridgeLift','14 mm','跨缝片距底高'),('PostWidth','24 mm','广告牌支架宽'),('PostThickness','6 mm','支架厚'),('PostHeight','150 mm','支架高'),('PostCentreLeft','=BillboardHalfWidth/2','左支架中心'),('PostCentreRight','=BillboardHalfWidth*1.5','右支架中心'),
('TextPixel','1 mm','原掩码像素尺寸'),('TextOverlap','0.1 mm','像素行融合扩张'),('TextThickness','1 mm','文字厚'),('TextOriginX','90 mm','文字掩码原点X'),('TextLovelyZ','332 mm','Lovely行原点Z'),('TextDrivenZ','304 mm','Driven行原点Z'),
('CouponWidth','70 mm','试件宽'),('CouponDepth','100 mm','底榫试件深'),('CouponBaseY','50 mm','底试榫中心'),('CouponBackHeight','80 mm','背试件高'),('CouponBackZ','48 mm','背试榫中心'),('NarrowCutFrom2','35 mm','模块2局部删除起点'),('NarrowCutTo2','165 mm','模块2局部删除终点'),('NarrowRemoved2','=NarrowCutTo2-NarrowCutFrom2','模块2缩短移除量'),('NarrowCutFrom5','30 mm','模块5局部删除起点'),('NarrowCutTo5','130 mm','模块5局部删除终点'),('NarrowRemoved5','=NarrowCutTo5-NarrowCutFrom5','模块5缩短移除量'),
('NarrowViewOffset5','135 mm','原缩短查看工程模块5平移'),
('PrintBrim','4 mm','原PLA brim'),('PrintBedWidth','256 mm','原打印床X'),('PrintBedDepth','256 mm','原打印床Y'),('PrintHeight','260 mm','原打印高度'),('ExportLinearDeflection','0.02 mm','新STL最大线性弦高（导出设置）'),
]


# Counts are dimensionless topology descriptors; changing component counts requires rebuilding.
PARAMETERS.extend([
    ('ModuleCount','=5','主体模块数量（无量纲；固定拓扑，改数量需重建）'),
    ('DeckLevelCount','=3','车库层数（无量纲；固定拓扑）'),
    ('ColumnCount','=4','承托柱数量（无量纲；固定拓扑）'),
    ('PrintWallLoops','4','原PLA墙圈数（无量纲）'),
    ('PrintInfillPercent','25','原PLA填充百分数（无量纲，25表示25%）'),
])

def sync_count_metadata(doc):
    sheet=doc.DesignParameters
    sheet.set('B1','Value: mm / count')
    for row,(alias,value,note) in enumerate(PARAMETERS,2):
        if alias not in {'ModuleCount','DeckLevelCount','ColumnCount','PrintWallLoops','PrintInfillPercent'}:continue
        sheet.set(f'A{row}',alias);sheet.set(f'B{row}',value);sheet.setAlias(f'B{row}',alias);sheet.set(f'C{row}',note);sheet.set(f'D{row}','derived' if value.startswith('=') else 'input')
    doc.recompute()


def create(doc):
    s=doc.addObject('Spreadsheet::Sheet','DesignParameters')
    s.set('A1','Alias');s.set('B1','Value: mm / count');s.set('C1','设计含义');s.set('D1','类型')
    for row,(alias,value,note) in enumerate(PARAMETERS,2):
        s.set(f'A{row}',alias);s.set(f'B{row}',value);s.setAlias(f'B{row}',alias);s.set(f'C{row}',note);s.set(f'D{row}','derived' if value.startswith('=') else 'input')
    s.setColumnWidth('A',200);s.setColumnWidth('B',180);s.setColumnWidth('C',280)
    doc.recompute();return s

def expression(value):
    # Prefix known aliases only; numeric constants are dimensionless multipliers.
    import re
    aliases={p[0] for p in PARAMETERS}
    return re.sub(r'\b[A-Za-z][A-Za-z0-9_]*\b',lambda m:'DesignParameters.'+m[0] if m[0] in aliases else m[0],str(value))

def evaluate(doc,value):
    result=doc.DesignParameters.evalExpression(expression(value))
    return result.Value if hasattr(result,'Value') else float(result)

def set_value(doc,alias,value):
    row=next(i for i,p in enumerate(PARAMETERS,2) if p[0]==alias)
    doc.DesignParameters.set(f'B{row}',value);doc.recompute()

def describe(root):
    (Path(root)/'reports/parameters.json').write_text(json.dumps([dict(alias=a,value=v,description=n,kind='derived' if v.startswith('=') else 'input') for a,v,n in PARAMETERS],ensure_ascii=False,indent=2))
