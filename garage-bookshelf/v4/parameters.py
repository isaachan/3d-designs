"""v4 dimensions in millimetres; spreadsheet expressions drive native CAD."""
import json
import re
from pathlib import Path

PARAMETERS = [
('Zero','0 mm','坐标基准'),
('OverallWidth','540 mm','主体总长，不含外挂蓝牌'),('GarageWidth','200 mm','车库段占地长'),
('BookWidth','=OverallWidth-GarageWidth','书架段占地长，含两侧6mm板'),
('BookModuleWidth','=BookWidth/2','两块书架主体等分'),
('OverallDepth','170 mm','总深，含广告牌'),('OverallHeight','238 mm','主体高，沿用v3'),
('BaseThickness','8 mm','底厚'),('BackThickness','5 mm','背厚'),('WallThickness','6 mm','隔板与右侧板厚'),
('BackRear','=OverallDepth-PostThickness','背板后表面，后方留支架厚度'),('BackFront','=BackRear-BackThickness','背板前表面'),('Overlap','0.2 mm','同一Body融合余量'),
('WallStart','=BaseThickness-Overlap','背板/侧板起高'),('WallPadLength','=OverallHeight-WallStart','竖板拉伸高'),
('PanelDepth','=BackFront','隔板深'),('RibSize','25 mm','书架板根三角肋边长'),('RibThickness','5 mm','三角肋厚'),
('RibFrontY','12 mm','前根肋'),('RibRearY','=BackFront-22 mm','后根肋'),
('TongueLength','14 mm','主体公榫长'),('SocketDepth','15 mm','主体母槽长'),('FitClearance','0.4 mm','燕尾槽名义总侧隙'),
('HalfClearance','=FitClearance/2','燕尾单侧间隙'),('SocketOvercut','0.2 mm','母槽上下越界'),
('BaseJointY1','42 mm','底榫中心1'),('BaseJointY2','=OverallDepth-42 mm','底榫中心2'),
('BackJointZ1','66 mm','背榫中心1'),('BackJointZ2','180 mm','背榫中心2'),
('BaseRootBottom','15 mm','底榫根底半宽'),('BaseRootTop','12 mm','底榫根顶半宽'),
('BaseTipBottom','12 mm','底榫尖底半宽'),('BaseTipTop','9 mm','底榫尖顶半宽'),
('BackFrontOverlap','0.2 mm','背榫向前融合'),('BackRootFront','13 mm','背榫根前半高'),('BackRootRear','17 mm','背榫根后半高'),
('BackTipFront','10 mm','背榫尖前半高'),('BackTipRear','14 mm','背榫尖后半高'),
('DeckEdgeGap','0.2 mm','层板与侧/背的每边间隙'),('DeckWidth','=GarageWidth-2*DeckEdgeGap','整层板宽'),
('DeckDepth','=BackFront-2*DeckEdgeGap','整层板深'),('DeckThickness','5 mm','层板面厚，沿用v3'),
('DeckFirstZ','66 mm','首层底高，沿用v3'),('DeckPitch','63 mm','层距，沿用v3'),
('DeckZ1','=DeckFirstZ','层1底高'),('DeckZ2','=DeckFirstZ+DeckPitch','层2底高'),('DeckZ3','=DeckFirstZ+2*DeckPitch','层3底高'),
('ColumnInset','14 mm','柱中心距车库左右边/前后边'),('ColumnX2','=GarageWidth-ColumnInset','右柱中心'),
('ColumnY2','=BackFront-ColumnInset','后柱中心'),('ColumnRadius','7 mm','分段柱轴半径'),('CollarRadius','10 mm','层板承托环半径'),
('CollarThickness','4 mm','托环厚'),('ConeHeight','=CollarRadius-ColumnRadius','45度锥肩高'),
('PinRadius','3 mm','定位销半径'),('PinClearance','0.25 mm','销孔单侧径向间隙'),('HoleRadius','=PinRadius+PinClearance','层板孔/柱底孔半径'),
('PegEngagement','3 mm','销插入上段长度'),('PegDepthGap','0.3 mm','柱底孔轴向余量'),('PinLength','=DeckThickness+PegEngagement','柱顶销长度'),
('SegmentHeight','=DeckPitch-DeckThickness','前三段柱高'),('ColumnTop','230 mm','柱顶沿用v3'),
('TopSegmentHeight','=ColumnTop-DeckZ3-DeckThickness','封顶柱段高'),
('BillboardWidth','=GarageWidth','整块广告牌宽'),('BillboardHeight','64 mm','沿用v3牌高'),('BillboardThickness','6 mm','广告牌厚'),
('BillboardBottom','300 mm','沿用v3牌底高'),('TotalHeight','=BillboardBottom+BillboardHeight','含广告牌总高'),
('BillboardY','=BackRear','广告牌/支架前表面位于背板后方，收进170mm总深'),
('PostWidth','24 mm','广告牌支架宽'),('PostThickness','6 mm','广告牌支架厚'),('PostBottom','150 mm','支架底高'),
('PostHeight','=BillboardBottom-PostBottom','支架高'),('PostX1','=GarageWidth/4-PostWidth/2','左支架X'),
('PostX2','=GarageWidth*3/4-PostWidth/2','右支架X'),
('TextPixel','1 mm','沿用v3字形，不缩小'),('TextOverlap','0.1 mm','字形像素融合'),('TextThickness','1 mm','白字厚'),
('TextOriginX','=GarageWidth/2-90 mm','字形居中'),('TextLovelyZ','332 mm','沿用v3上行文字高'),('TextDrivenZ','304 mm','沿用v3下行文字高'),
('SignThickness','2 mm','正面蓝牌前后厚'),('SignWidth','36 mm','正面蓝牌左右宽'),('SignHeight','180 mm','右侧蓝牌高'),
('SignX','=OverallWidth','蓝牌位于右侧板外边的X起点'),('OverallEnvelopeWidth','=OverallWidth+SignWidth','含外挂蓝牌的最大总长'),('SignFrontY','0 mm','蓝牌朝向使用者的前表面Y'),('SignZ','50 mm','蓝牌Z'),('SignMountDepth','14 mm','蓝牌一体折边沿右侧板外表面的贴合深度'),
('PrintBrim','4 mm','打印床四边预留brim'),('PrintBedWidth','235.5 mm','按附图较小X范围保守校核'),
('PrintBedDepth','256 mm','附图Y范围'),('PrintHeight','256 mm','按附图较小Z范围保守校核'),
]


def expression(value):
    aliases={p[0] for p in PARAMETERS}
    return re.sub(r'\b[A-Za-z][A-Za-z0-9_]*\b',lambda m:'DesignParameters.'+m[0] if m[0] in aliases else m[0],str(value))


def evaluate(doc,value):
    v=doc.DesignParameters.evalExpression(expression(value))
    return v.Value if hasattr(v,'Value') else float(v)


def create(doc):
    s=doc.addObject('Spreadsheet::Sheet','DesignParameters')
    for col,text in zip('ABCD',['Alias','Value (mm)','说明','类型']):s.set(col+'1',text)
    for row,(alias,value,note) in enumerate(PARAMETERS,2):
        s.set(f'A{row}',alias);s.set(f'B{row}',value);s.setAlias(f'B{row}',alias)
        s.set(f'C{row}',note);s.set(f'D{row}','derived' if value.startswith('=') else 'input')
    for col,w in [('A',200),('B',210),('C',310)]:s.setColumnWidth(col,w)
    doc.recompute()
    return s


def set_value(doc,alias,value):
    row=next(i for i,p in enumerate(PARAMETERS,2) if p[0]==alias)
    doc.DesignParameters.set(f'B{row}',value);doc.recompute()


def describe(root):
    (Path(root)/'reports/parameters.json').write_text(json.dumps([dict(alias=a,value=v,description=n) for a,v,n in PARAMETERS],ensure_ascii=False,indent=2))
