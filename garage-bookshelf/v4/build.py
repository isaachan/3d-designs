"""Self-contained v4 builder. Run with FreeCAD's bundled Python."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as App
from parameters import create,expression
from assembly import group,part
from geometry.sketches import rectangle,circle,plane
from geometry.features import pad,pocket,loft,finish
from connectors import dovetail
import Part,Sketcher
import cosmetics


def reversed_pocket(body,name,sketch,length):
    f=body.newObject('PartDesign::Pocket',name);f.Profile=sketch
    f.setExpression('Length',expression(length));f.Reversed=True;f.Refine=True
    return finish(body,f)


def circles(body,name,centres,radius,z):
    from parameters import evaluate
    s=plane(body,name,offset=('Zero','Zero',z));d=body.Document
    for x,y in centres:
        i=s.addGeometry(Part.Circle(App.Vector(evaluate(d,x),evaluate(d,y),0),App.Vector(0,0,1),evaluate(d,radius)),False)
        for kind,val in [('DistanceX',x),('DistanceY',y),('Radius',radius)]:
            args=(kind,i,evaluate(d,val)) if kind=='Radius' else (kind,i,3,evaluate(d,val))
            c=s.addConstraint(Sketcher.Constraint(*args));s.setExpression(f'Constraints[{c}]',expression(val))
    d.recompute()
    assert s.FullyConstrained
    return s


CENTRES=[('ColumnInset','ColumnInset'),('ColumnX2','ColumnInset'),('ColumnInset','ColumnY2'),('ColumnX2','ColumnY2')]


def module(body,index):
    width='GarageWidth' if index==1 else 'BookModuleWidth'
    pad(body,'Pad_Base',rectangle(body,'Sketch_Base',width,'OverallDepth'),'BaseThickness')
    pad(body,'Pad_Back',rectangle(body,'Sketch_Back',width,'BackThickness',origin=('Zero','BackFront'),offset=('Zero','Zero','WallStart')),'WallPadLength')
    if index in (2,3):
        x='Zero' if index==2 else 'BookModuleWidth-WallThickness'
        pad(body,'Pad_Upright',rectangle(body,'Sketch_Upright','WallThickness','PanelDepth',origin=(x,'Zero'),offset=('Zero','Zero','WallStart')),'WallPadLength')
    if index==1:
        pad(body,'Pad_ColumnBasePins',circles(body,'Sketch_ColumnBasePins',CENTRES,'PinRadius','BaseThickness'),'PegEngagement')
    if index<3:
        for n in (1,2):
            dovetail(body,f'BaseTongue{n}','base',f'{width}-Overlap',f'BaseJointY{n}')
            dovetail(body,f'BackTongue{n}','back',f'{width}-Overlap',f'BackJointZ{n}')
    if index>1:
        for n in (1,2):
            dovetail(body,f'BaseSocket{n}','base','-Overlap',f'BaseJointY{n}',True)
            dovetail(body,f'BackSocket{n}','back','-Overlap',f'BackJointZ{n}',True)


def deck(body):
    pad(body,'Pad_WholeDeck',rectangle(body,'Sketch_WholeDeck','DeckWidth','DeckDepth'),'DeckThickness')
    centres=[(f'{x}-DeckEdgeGap',f'{y}-DeckEdgeGap') for x,y in CENTRES]
    pocket(body,'Pocket_FourLocatingHoles',circles(body,'Sketch_FourLocatingHoles',centres,'HoleRadius','DeckThickness'),'DeckThickness')


def column(body,top=False):
    h='TopSegmentHeight' if top else 'SegmentHeight'
    pad(body,'Pad_Shaft',circle(body,'Sketch_Shaft','ColumnRadius','Zero'),h if top else f'{h}-CollarThickness-ConeHeight')
    if not top:
        root=circle(body,'Sketch_ConeRoot','ColumnRadius',f'{h}-CollarThickness-ConeHeight')
        tip=circle(body,'Sketch_ConeTop','CollarRadius',f'{h}-CollarThickness')
        loft(body,'Loft_SupportCone',root,tip)
        pad(body,'Pad_Collar',circle(body,'Sketch_Collar','CollarRadius',f'{h}-CollarThickness'),'CollarThickness')
        pad(body,'Pad_ThroughDeckPin',circle(body,'Sketch_ThroughDeckPin','PinRadius',h),'PinLength')
    reversed_pocket(body,'Pocket_BottomSocket',circle(body,'Sketch_BottomSocket','HoleRadius','Zero'),'PegEngagement+PegDepthGap')


def build():
    doc=App.newDocument('GarageBookshelfV4');create(doc)
    main=group(doc,'Modules','01 主体：200 + 145 + 145 mm')
    for i,x in [(1,'Zero'),(2,'GarageWidth'),(3,'GarageWidth+BookModuleWidth')]:
        _,b=part(doc,main,f'module_{i}',f'主体模块 {i}',(x,'Zero','Zero'));module(b,i)
        if i==1:
            from parking_recesses import add_recesses
            from parking_markings import add_recessed
            add_recesses(b,2,base=True);add_recessed(b,2,1)
    garage=group(doc,'Garage','02 三块整片层板与分段立柱')
    for lev in (1,2,3):
        _,b=part(doc,garage,f'garage_deck_{lev}',f'整块停车层板 {lev}',('DeckEdgeGap','DeckEdgeGap',f'DeckZ{lev}'));deck(b)
        from parking_markings import add_recessed,LAYOUTS
        from parking_recesses import add_recesses
        add_recesses(b,LAYOUTS[lev]);add_recessed(b,LAYOUTS[lev],lev+1)
    for n,(x,y) in enumerate(CENTRES,1):
        for segment,z in enumerate(('BaseThickness','DeckZ1+DeckThickness','DeckZ2+DeckThickness','DeckZ3+DeckThickness'),1):
            _,b=part(doc,garage,f'column_{n}_segment_{segment}',f'立柱 {n} 第{segment}段',(x,y,z),color='columns');column(b,segment==4)
    board=group(doc,'Billboard','03 整块广告牌与原字形')
    _,b=part(doc,board,'billboard','整块广告牌',('Zero','BillboardY','BillboardBottom'),color='billboard')
    cosmetics.box(b,'BillboardWidth','BillboardThickness','BillboardHeight')
    for side,x in [('left','PostX1'),('right','PostX2')]:
        _,b=part(doc,board,'billboard_post_'+side,'广告牌支架 '+side,(x,'BillboardY','PostBottom'),color='billboard');cosmetics.box(b,'PostWidth','PostThickness','PostHeight')
    cosmetics.text(doc,board,'billboard_text_lovely_cars','Lovely Cars 白字',332)
    cosmetics.text(doc,board,'billboard_text_ive_driven',"I've Driven 白字",304)
    signs=group(doc,'Signs','04 右侧外挂蓝牌（不计入490mm主体）')
    _,b=part(doc,signs,'book_depot_sign','朝向使用者的右侧外挂蓝牌',('SignX','SignFrontY','SignZ'),color='sign')
    cosmetics.box(b,'SignWidth','SignThickness','SignHeight')
    pad(b,'Pad_ExternalMountingReturn',rectangle(b,'Sketch_ExternalMountingReturn','SignThickness','SignMountDepth-SignThickness',origin=('Zero','SignThickness')),'SignHeight')
    cosmetics.sign_lettering(b)
    from parking_recesses import add_interface_sample
    add_interface_sample(doc)
    doc.recompute()
    return doc
