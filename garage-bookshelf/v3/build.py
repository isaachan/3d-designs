import FreeCAD as App
from parameters import create
from assembly import group,part
from components import modules,shelves,columns,cosmetics,coupons

def document(name):
    if name in App.listDocuments():App.closeDocument(name)
    d=App.newDocument(name);create(d);return d

def assembly():
    d=document('GarageBookshelfParametric')
    main=group(d,'Modules','01 五个一体主体模块（灰色）')
    for i in range(1,6):
        _,b=part(d,main,f'module_{i}',f'主体模块 {i}',(f'ModuleStart{i}','Zero','Zero'));modules.build(b,i)
    garage=group(d,'Garage','02 车库层板与立柱')
    for lev in (1,2,3):
        for side in ('left','right'):
            _,b=part(d,garage,f'garage_deck_{lev}_{side}',f'停车层板 {lev} {"左" if side=="left" else "右"}',('Zero' if side=='left' else 'DeckHalfWidth','Zero',f'DeckZ{lev}'));shelves.build(b,side=='right')
        _,b=part(d,garage,f'garage_deck_{lev}_seam_bridge',f'停车层板 {lev} 底面跨缝加强片',('DeckBridgeX','DeckBridgeY',f'DeckZ{lev}-DeckBridgeThickness'));cosmetics.box(b,'DeckBridgeWidth','DeckBridgeDepth','DeckBridgeThickness')
    for i,(x,y) in enumerate((('Zero','Zero'),('ColumnPitchX','Zero'),('Zero','ColumnPitchY'),('ColumnPitchX','ColumnPitchY')),1):
        _,b=part(d,garage,f'garage_column_{i}',f'黄色承托柱 {i}',(f'{x}+ColumnCentreOffset',f'{y}+ColumnCentreOffset','BaseThickness'),color='columns');columns.build(b)
    signs=group(d,'Signs','03 右侧竖牌')
    _,b=part(d,signs,'book_depot_sign','BOOK DEPOT 蓝色底牌',('OverallWidth','SignThickness','SignBaseZ'),App.Rotation(App.Vector(1,0,0),90),color='sign');cosmetics.box(b,'SignWidth','SignHeight','SignThickness')
    board=group(d,'Billboard','04 Lovely Cars I’ve Driven 广告牌')
    for side,x in [('left','Zero'),('right','BillboardHalfWidth')]:
        _,b=part(d,board,'billboard_'+side,'广告牌'+('左板' if side=='left' else '右板'),(x,'OverallDepth','BillboardBottom'),color='billboard');cosmetics.box(b,'BillboardHalfWidth','BillboardThickness','BillboardHeight')
    _,b=part(d,board,'billboard_seam_bridge','广告牌背面跨缝片',('BillboardHalfWidth-BillboardBridgeWidth/2','OverallDepth+BillboardThickness','BillboardBottom+BillboardBridgeLift'),color='billboard');cosmetics.box(b,'BillboardBridgeWidth','BillboardBridgeThickness','BillboardBridgeHeight')
    for side,center in [('left','PostCentreLeft'),('right','PostCentreRight')]:
        _,b=part(d,board,'billboard_post_'+side,'广告牌'+('左' if side=='left' else '右')+'支架',(f'{center}-PostWidth/2','OverallDepth','BillboardBottom-PostHeight'),color='billboard');cosmetics.box(b,'PostWidth','PostThickness','PostHeight')
    cosmetics.text(d,board,'billboard_text_lovely_cars','Lovely Cars 白色文字',332)
    cosmetics.text(d,board,'billboard_text_ive_driven',"I've Driven 白色文字",304)
    d.recompute();return d

def auxiliary():
    d=document('GarageBookshelfAuxiliary');tests=group(d,'FitTests','01 原尺寸接口试件')
    for kind in ('base','back','corner'):
        for male in (True,False):
            name='test_'+kind+('_left_four_male' if male else '_right_four_female') if kind=='corner' else f'test_{kind}_{"male" if male else "female"}'
            x='CouponWidth' if kind=='corner' and not male else 'Zero'
            _,b=part(d,tests,name,name,(x,'Zero','Zero'));coupons.build(b,kind,male)
    narrow=group(d,'Narrow','02 缩短外观件（不可装配/承重）')
    for i in (2,5):
        _,b=part(d,narrow,f'module_{i}_narrow_visual',f'模块{i}缩短外观件',(f'ModuleStart{i}'+('+NarrowViewOffset5' if i==5 else ''),'Zero','Zero'));modules.build(b,i,width=f'ModuleWidth{i}-NarrowRemoved{i}',removed=f'NarrowRemoved{i}')
    d.recompute();return d
