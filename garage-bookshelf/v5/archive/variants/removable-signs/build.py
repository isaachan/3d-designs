# Frozen v4 source; use v5/tools or the migrated studies.
if __name__ == '__main__':
    raise SystemExit('Historical entry disabled; see v5/README.md and archive/README.md')

"""Native FreeCAD retrofit of the 490 mm v4 assembly. Original v4 stays frozen."""
import sys,json,itertools,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent
sys.path.insert(0,str(BASE))
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as App,Part,Mesh,MeshPart
from assembly import part,group,global_shape,parts,bodies
from geometry.sketches import rectangle,loops,circle
from geometry.features import pad,pocket,finish
from parameters import PARAMETERS,evaluate,expression
import cosmetics
NEW=[('RailNeckHalf','1.1 mm','公燕尾颈部半宽'),('RailRootHalf','2.6 mm','公燕尾根部半宽'),('SlotNeckHalf','1.6 mm','母槽开口半宽'),('SlotRootHalf','3.2 mm','母槽深部半宽'),('RailDepth','1.6 mm','公轨进入牌座深度'),('SlotDepth','1.9 mm','母槽深度'),('CarrierFront','=-2 mm','字牌正面相对牌座'),('CarrierBack','=-0.2 mm','字牌背面相对牌座')]
PARAMETERS.extend(NEW)

def hole(body,name,x,z,y,length):
    # XZ sketch normal points toward -Y; reversed pad direction is irrelevant to Pocket.
    from geometry.sketches import plane
    import Sketcher
    s=plane(body,name,orientation='XZ',offset=('Zero',str(y),'Zero'))
    i=s.addGeometry(Part.Circle(App.Vector(x,z,0),App.Vector(0,0,1),1.65),False)
    for kind,args in [('DistanceX',(i,3,x)),('DistanceY',(i,3,z)),('Radius',(i,1.65))]:s.addConstraint(Sketcher.Constraint(kind,*args))
    body.Document.recompute();assert s.FullyConstrained
    return pocket(body,'Pocket_'+name,s,str(length))

def rail(body,name,center,start,length,vertical=False,female=False):
    center=f'{center} mm'
    neck='SlotNeckHalf' if female else 'RailNeckHalf'
    root='SlotRootHalf' if female else 'RailRootHalf'
    shallow='-0.01 mm' if female else 'CarrierBack-0.01 mm'
    deep='SlotDepth' if female else 'RailDepth'
    # female surface is slightly overcut to open the groove cleanly.
    poly=[(f'{center}-{neck}',shallow),(f'{center}+{neck}',shallow),(f'{center}+{root}',deep),(f'{center}-{root}',deep)]
    if vertical:
        s=loops(body,name,[poly],orientation='XY',offset=('Zero','Zero',f'{start} mm'))
    else:
        s=loops(body,name,[[(y,x) for x,y in poly]],orientation='YZ',offset=(f'{start} mm','Zero','Zero'))
    f=body.newObject('PartDesign::Pocket' if female else 'PartDesign::Pad',('Pocket_' if female else 'Pad_')+name)
    f.Profile=s;f.Length=length;f.Refine=True
    if female:f.Reversed=True
    return finish(body,f)

def remove_part(doc,name):
    p=doc.getObject(name)
    def delete(o):
        for child in list(getattr(o,'Group',[])):delete(child)
        doc.removeObject(o.Name)
    delete(p)

def build():
    d=App.openDocument(str(BASE/'garage-bookshelf-v4-assembly.FCStd'))
    for row,(alias,value,note) in enumerate(NEW,len(PARAMETERS)-len(NEW)+2):
        for col,text in [('A',alias),('B',value),('C',note),('D','input')]:d.DesignParameters.set(f'{col}{row}',text)
        d.DesignParameters.setAlias(f'B{row}',alias)
    d.recompute()
    # Keep original white letters as a one-time glued decoration on the sliding carrier.
    for name in ['billboard_text_lovely_cars','billboard_text_ive_driven']:
        d.getObject(name).setExpression('Placement.Base.y',expression('BillboardY+CarrierFront'))
    top=d.billboard_Body
    for z in [9,23,39,53]:rail(top,f'TopSlot{z}',z,4.7,195.5,female=True)
    hole(top,'TopLock31',190,31,0,3.2)
    kit=group(d,'RemovableLettering','05 可抽换字牌及锁销')
    _,b=part(d,kit,'top_carrier','两行一体可换字牌',('5 mm','BillboardY','302 mm'),color='billboard')
    pad(b,'Pad_Carrier',rectangle(b,'Sketch_Carrier','190 mm','58 mm',orientation='XZ',offset=('Zero','CarrierBack','Zero')),'1.8 mm')
    for c in [7,21,37,51]:rail(b,f'CarrierRail{c}',c,0,190)
    hole(b,'CarrierLock',185,29,-2,1.8)
    remove_part(d,'book_depot_sign')
    _,b=part(d,d.Signs,'side_receiver','右侧燕尾牌座',('SignX','Zero','SignZ'),color='sign')
    cosmetics.box(b,'SignWidth','4 mm','SignHeight')
    pad(b,'Pad_MountReturn',rectangle(b,'Sketch_MountReturn','2 mm','10 mm',origin=('Zero','4 mm')),'SignHeight')
    for c in [10,38]:rail(b,f'SideSlot{c}',c,3.7,176.5,vertical=True,female=True)
    hole(b,'SideLock',24,12,0,3.2)
    _,b=part(d,kit,'side_cartridge','竖向可抽换口号字牌',('SignX','Zero','SignZ'),color='sign')
    pad(b,'Pad_Carrier',rectangle(b,'Sketch_Carrier','44 mm','172 mm',origin=('2 mm','4 mm'),orientation='XZ',offset=('Zero','CarrierBack','Zero')),'1.8 mm')
    for c in [10,38]:rail(b,f'SideRail{c}',c,4,172,vertical=True)
    # Existing exact glyph outlines, now recessed in the removable carrier.
    data=json.loads((BASE/'reference/sign-lettering.json').read_text());sketches=[]
    b.addProperty('App::PropertyString','EngravedSlogan');b.EngravedSlogan=data['slogan']
    longest=max(r['width_per_cap_height'] for r in data['lines']);top_expr=f'(SignHeight+{longest:.12g}*SignTextHeight)/2'
    for index,row in enumerate(data['lines'],1):
        origin=f'(SignWidth-2*SignTextHeight-SignColumnGap)/2+{index-1}*(SignTextHeight+SignColumnGap)'
        for n,indices in enumerate(row['glyphs'],1):
            polygons=[[(f'{origin}+({y:.12g})*SignTextHeight',f'{top_expr}-({x:.12g})*SignTextHeight') for x,y in row['polygons'][i]] for i in indices]
            sketches.append(loops(b,f'Sketch_Slogan{index}_{n}',polygons,orientation='XZ',offset=('Zero','CarrierFront','Zero')))
    cosmetics.engrave_sign_sketches(b,sketches)
    hole(b,'SideCarrierLock',24,12,-2,1.8)
    for n,(x,y,z) in enumerate([('190 mm','BillboardY-3.2 mm','331 mm'),('SignX+24 mm','-3.2 mm','SignZ+12 mm')],1):
        _,b=part(d,kit,f'lock_pin_{n}','可拔定位销 '+str(n),(x,y,z),rotation=App.Rotation(App.Vector(1,0,0),-90),color='columns')
        pad(b,'Pad_Head',circle(b,'Sketch_Head','3 mm','Zero'),'1.2 mm')
        pad(b,'Pad_Pin',circle(b,'Sketch_Pin','1.5 mm','1.2 mm'),'5 mm')
    d.Label='车库书架 · 49cm · 可抽换字牌'
    d.recompute()
    return d

NAMES=['billboard','top_carrier','side_receiver','side_cartridge','lock_pin_1']
def validate_export(d):
    bs=[o for o in d.Objects if o.TypeId=='PartDesign::Body']
    assert all(b.Shape.isValid() and len(b.Shape.Solids)==1 for b in bs)
    sketches=[o for o in d.Objects if o.TypeId=='Sketcher::SketchObject'];assert all(s.FullyConstrained for s in sketches)
    shapes={b.Name:global_shape(b) for b in bs};bad=[]
    for a,b in itertools.combinations(shapes,2):
        if shapes[a].BoundBox.intersect(shapes[b].BoundBox):
            v=shapes[a].common(shapes[b]).Volume
            if v>.01:bad.append((a,b,v))
    assert not bad,bad
    paths=[]
    for moving,receiver,axis,offsets in [('top_carrier','billboard',App.Vector(1,0,0),[201,150,75,10,1,0]),('side_cartridge','side_receiver',App.Vector(0,0,1),[181,120,60,10,1,0])]:
        s=shapes[moving+'_Body'];fixed=[v for k,v in shapes.items() if k!=moving+'_Body' and not k.startswith('lock_pin') and not k.startswith('billboard_text')]
        for offset in offsets:
            moved=s.copy();moved.translate(axis*offset)
            v=sum(moved.common(f).Volume for f in fixed);assert v<.01,(moving,offset,v)
            paths.append(dict(part=moving,offset_mm=offset,overlap_mm3=v))
        # A forward pull must be mechanically blocked by the dovetail undercut.
        pulled=s.copy();pulled.translate(App.Vector(0,-.8,0))
        assert pulled.common(shapes[receiver+'_Body']).Volume>1
        # With the locking pin seated, sliding must be blocked.
        moved=s.copy();moved.translate(axis*1)
        pin=shapes['lock_pin_'+str(1 if moving=='top_carrier' else 2)+'_Body']
        assert moved.common(pin).Volume>.01
    records=[]
    for old in ['top_carrier_lower.stl','top_carrier_upper.stl']:
        (ROOT/'print-stl'/old).unlink(missing_ok=True)
    for name in NAMES:
        b=d.getObject(name+'_Body');shape=b.Shape.copy()
        # Receiver and carrier faces on bed; rail bevels grow upward at <45 degrees.
        rot=App.Rotation(App.Vector(1,0,0),90) if not name.startswith('lock_pin') else App.Rotation()
        mesh=MeshPart.meshFromShape(Shape=shape,LinearDeflection=.02,AngularDeflection=.12,Relative=False)
        mesh.transform(App.Placement(App.Vector(),rot).toMatrix());bb=mesh.BoundBox;mesh.translate(-bb.XMin,-bb.YMin,-bb.ZMin)
        f=ROOT/'print-stl'/f'{name}.stl';mesh.write(str(f));check=Mesh.Mesh(str(f));assert check.isSolid() and not check.hasNonManifolds()
        bb=check.BoundBox;dims=[bb.XLength,bb.YLength,bb.ZLength];assert dims[0]+8<235.5 and dims[1]+8<256 and dims[2]<256
        records.append(dict(name=name,quantity=2 if name.startswith('lock_pin') else 1,dimensions_mm=dims,sha256=hashlib.sha256(f.read_bytes()).hexdigest()))
    Part.makeCompound(list(shapes.values())).exportStep(str(ROOT/'removable-signs-assembly.step'))
    report=dict(status='passed',bodies=len(bs),fully_constrained_sketches=len(sketches),interfering_pairs=bad,insertion_paths=paths,forward_pull_blocked=True,sliding_blocked_by_lock_pins=True,slot_depth_mm=1.9,side_receiver_remaining_back_mm=2.1,minimum_rail_side_clearance_mm=.33,rail_depth_clearance_mm=.3,front_gap_mm=.2,print_parts=records,physical_fit='not_tested',baseline_cad_sha256=hashlib.sha256((BASE/'garage-bookshelf-v4-assembly.FCStd').read_bytes()).hexdigest())
    (ROOT/'reports/validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print('PASS geometry, sliding, dovetail capture, locking pins, print meshes',flush=True)

if __name__=='__main__':
    d=build();d.saveAs(str(ROOT/'removable-signs-assembly.FCStd'))
    validate_export(d)
    App.closeDocument(d.Name);d=App.openDocument(str(ROOT/'removable-signs-assembly.FCStd'))
    assert all(b.Shape.isValid() for b in d.Objects if b.TypeId=='PartDesign::Body')
    print('PASS saved CAD reopened',flush=True)
