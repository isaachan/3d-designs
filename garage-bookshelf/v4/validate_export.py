"""Validate exact solids, mating paths, editable CAD and exported print meshes."""
import sys,json,itertools,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as App,Part,Mesh,MeshPart
from assembly import global_shape,parts,bodies
from parameters import evaluate,set_value,describe


def native(doc):
    bs=[o for o in doc.Objects if o.TypeId=='PartDesign::Body']
    ss=[o for o in doc.Objects if o.TypeId=='Sketcher::SketchObject']
    assert len(bs)==46,len(bs)
    assert ss and all(s.FullyConstrained for s in ss)
    assert all(b.Shape.isValid() and len(b.Shape.Solids)==1 for b in bs)
    invalid=[(o.Name,list(o.State)) for o in doc.Objects if any(k in o.State for k in ['Invalid','Error'])]
    assert not invalid,invalid
    assert not any(o.TypeId in ['Part::Feature','Mesh::Feature','PartDesign::Feature'] for o in doc.Objects)
    return dict(bodies=len(bs),sketches=len(ss),fully_constrained=True,single_solid_each=True,invalid_objects=invalid)


def assembly(doc):
    shapes={b.Name:global_shape(b) for p in parts(doc).values() for b in bodies(p)}
    bad=[]
    for a,b in itertools.combinations(shapes,2):
        if not shapes[a].BoundBox.intersect(shapes[b].BoundBox):continue
        v=shapes[a].common(shapes[b]).Volume
        if v>0.01:bad.append(dict(a=a,b=b,volume_mm3=v))
    assert not bad,bad
    bb=Part.makeCompound(list(shapes.values())).optimalBoundingBox()
    dims=[bb.XLength,bb.YLength,bb.ZLength]
    assert all(abs(a-b)<1e-5 for a,b in zip(dims,[540,170,364])),dims
    paths=[]
    for i in (1,2):
        a=shapes[f'module_{i}_Body'];b=shapes[f'module_{i+1}_Body']
        for offset in (30,15,5,1,0):
            s=b.copy();s.translate(App.Vector(offset,0,0));v=a.common(s).Volume
            assert v<.01,(i,offset,v)
            paths.append(dict(interface=i,positive_x_offset_mm=offset,overlap_mm3=v))
    # A deck is lowered onto its four supporting segments before the next four are installed.
    deck_paths=[];contacts=[]
    from build import CENTRES
    for lev in (1,2,3):
        plate=shapes[f'garage_deck_{lev}_Body'];z=evaluate(doc,f'DeckZ{lev}')
        fixed=[shapes[f'column_{n}_segment_{lev}_Body'] for n in range(1,5)]
        fixed.append(shapes['module_1_Body']);fixed.append(shapes['module_2_Body'])
        for dz in (12,8,3,0):
            moved=plate.copy();moved.translate(App.Vector(0,0,dz))
            v=sum(moved.common(s).Volume for s in fixed)
            assert v<.01,(lev,dz,v)
            deck_paths.append(dict(level=lev,upward_offset_mm=dz,overlap_mm3=v))
        for n,(x,y) in enumerate(CENTRES,1):
            slab=Part.makeCylinder(evaluate(doc,'CollarRadius'),.05,App.Vector(evaluate(doc,x),evaluate(doc,y),z))
            area=plate.common(slab).Volume/.05
            target=3.141592653589793*(evaluate(doc,'CollarRadius')**2-evaluate(doc,'HoleRadius')**2)
            assert abs(area-target)<.01,(area,target)
            contacts.append(dict(level=lev,column=n,bearing_area_mm2=round(area,3)))
    return dict(bounds_mm=[bb.XMin,bb.YMin,bb.ZMin,bb.XMax,bb.YMax,bb.ZMax],dimensions_mm=dims,interfering_pairs=bad,module_insertion_paths=paths,deck_lowering_paths=deck_paths,collar_contact_areas=contacts)


def parameter_test(doc):
    set_value(doc,'OverallDepth','172 mm')
    assert abs(doc.module_1_Body.Shape.BoundBox.YLength-172)<1e-5
    assert abs(doc.garage_deck_1_Body.Shape.BoundBox.YLength-166.6)<1e-5
    y=doc.column_3_segment_1.getGlobalPlacement().Base.y
    assert abs(y-153)<1e-5,y
    set_value(doc,'OverallDepth','170 mm')
    set_value(doc,'GarageWidth','202 mm')
    assert abs(doc.garage_deck_1_Body.Shape.BoundBox.XLength-201.6)<1e-5
    assert abs(doc.module_2.getGlobalPlacement().Base.x-202)<1e-5
    assert abs(evaluate(doc,'BookModuleWidth')-169)<1e-5
    set_value(doc,'GarageWidth','200 mm')
    native(doc)
    return dict(depth_170_to_172_to_170='passed',garage_200_to_202_to_200='passed',body_deck_columns_and_modules_follow=True)


def export(doc):
    for sub in ['stl','print-stl']: (ROOT/sub).mkdir(exist_ok=True)
    records=[]
    for name,p in parts(doc).items():
        ss=[global_shape(b) for b in bodies(p)]
        shape=ss[0] if len(ss)==1 else Part.makeCompound(ss)
        mesh=MeshPart.meshFromShape(Shape=shape,LinearDeflection=.02,AngularDeflection=.12,Relative=False)
        mesh.write(str(ROOT/'stl'/f'{name}.stl'))
        rotation=App.Rotation()
        orient='原方向，底面朝下'
        if name.startswith('garage_deck'):
            rotation=App.Rotation(App.Vector(1,0,0),180);orient='平整顶面贴床，加强梁向上'
        elif name.startswith('billboard'):
            rotation=App.Rotation(App.Vector(1,0,0),90);orient='牌/文字/支架放平'
        elif name=='book_depot_sign':
            rotation=App.Rotation(App.Vector(0,1,0),90);orient='蓝牌大面贴床'
        m=Mesh.Mesh(mesh);m.transform(App.Placement(App.Vector(),rotation).toMatrix())
        bb=m.BoundBox;m.translate(-bb.XMin,-bb.YMin,-bb.ZMin)
        file=ROOT/'print-stl'/f'{name}.stl';m.write(str(file))
        check=Mesh.Mesh(str(file));bb=check.BoundBox;dims=[bb.XLength,bb.YLength,bb.ZLength]
        count=len(ss)
        assert check.isSolid() and not check.hasNonManifolds()
        assert len(check.getSeparateComponents())==count,(name,len(check.getSeparateComponents()),count)
        assert dims[0]+8<=235.501 and dims[1]+8<=256.001 and dims[2]<=256.001,(name,dims)
        records.append(dict(name=name,file=str(file.relative_to(ROOT)),quantity=1,solid_components=count,closed=True,non_manifold=False,dimensions_mm=dims,orientation=orient,with_4mm_brim_within_235_5_256_256=True,sha256=hashlib.sha256(file.read_bytes()).hexdigest()))
    all_shapes=[global_shape(b) for p in parts(doc).values() for b in bodies(p)]
    Part.makeCompound(all_shapes).exportStep(str(ROOT/'garage-bookshelf-v4-assembly.step'))
    step=Part.Shape()
    step.read(str(ROOT/'garage-bookshelf-v4-assembly.step'))
    bb=step.optimalBoundingBox()
    assert len(step.Solids)==46,len(step.Solids)
    assert all(abs(a-b)<.001 for a,b in zip([bb.XLength,bb.YLength,bb.ZLength],[540,170,364])),str(bb)
    return records


def main():
    file=ROOT/'garage-bookshelf-v4-assembly.FCStd'
    doc=App.openDocument(str(file));doc.recompute()
    nr=native(doc);a=assembly(doc);p=parameter_test(doc)
    out=export(doc);describe(ROOT)
    # Parameter round-trip is not saved into the original CAD; recheck saved delivery on reopen.
    App.closeDocument(doc.Name)
    doc=App.openDocument(str(file));doc.recompute();native(doc);assembly(doc)
    report=dict(status='passed',native=nr,assembly=a,parameter_edit=p,saved_file_reopen='passed',print_parts=out,
                physical_fit_and_load='not_tested',printer_reference='user supplied screenshot; conservative 235.5 x 256 x 256 mm; 4 mm brim each side')
    (ROOT/'reports/validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    bom=[dict(name=r['name'],quantity=r['quantity'],print_file=r['file'],dimensions_mm=r['dimensions_mm']) for r in out]
    (ROOT/'reports/bom.json').write_text(json.dumps(bom,ensure_ascii=False,indent=2))
    print('PASS',nr,len(out),'print files')

if __name__=='__main__':main()
