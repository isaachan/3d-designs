"""Apply the approved wide-accessible decoration to the four existing floors.

Incremental native-CAD edit; preserves unrelated bodies, F joints, removable
lettering and corner fillets. Validate a candidate before replacing formal CAD.
No STEP, STL, 3MF, print settings or ZIP deliveries are regenerated.
"""
import hashlib
import itertools
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as App,Part
from assembly import global_shape
from decoration.recessed_layout import FLOORS,bay_edges
from parameters import evaluate
from parking_markings import add_recessed,masks
from parking_recesses import add_recesses,center_x
from update_parking_recesses import valid,floor_height

EXPECTED_SHA256='ab3e0f584073b005c27cfd52e6d21da304093adec2c02e44d36ce911cee54da2'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def print_files():
    return {str(p.relative_to(ROOT)):sha(p) for p in ROOT.rglob('*')
            if p.is_file() and p.suffix.lower() in ('.step','.stl','.3mf','.zip')}


def endpoints(edge):
    return sorted(tuple(round(x,6) for x in v.Point) for v in edge.Vertexes)


def retire_old_surface(body):
    doc=body.Document
    fillet=next(o for o in body.Group if o.TypeId=='PartDesign::Fillet' and o.Name.startswith('Fillet_ExposedCorners'))
    if body.SourcePart!='module_1':
        old,edges=fillet.Base
        pairs=[endpoints(old.Shape.Edges[int(name[4:])-1]) for name in edges]
        blank=next(o for o in body.Group if o.TypeId=='PartDesign::Pocket' and o.Name.startswith('Pocket_FourLocatingHoles'))
        mapped=[]
        for pair in pairs:
            found=[f'Edge{i}' for i,e in enumerate(blank.Shape.Edges,1) if endpoints(e)==pair]
            assert len(found)==1,(body.Name,pair,found)
            mapped.extend(found)
        fillet.Base=(blank,mapped)
    body.Tip=fillet
    retired=[]
    for obj in reversed(list(body.Group)):
        marking='ParkingMarkingColor' in obj.PropertiesList or obj.Name.startswith(('Pocket_ParkingBlue','Pocket_ParkingYellow','Pocket_ParkingWhite'))
        recess=obj.Name.startswith(('Sketch_ParkingTrayRecesses','Pocket_ParkingTrayRecesses','Chamfer_ParkingTrayEntries'))
        if marking or recess:
            retired.append(obj.Name);doc.removeObject(obj.Name)
    body.Tip=fillet;doc.recompute()
    assert body.Shape.isValid() and len(body.Shape.Solids)==1,body.Name
    return retired


def verify(doc,original,original_global):
    result={'native':valid(doc)}
    all_bodies=[b for b in doc.Objects if b.TypeId=='PartDesign::Body']
    modified={name+'_Body' for name in FLOORS}
    unchanged=[]
    for body in all_bodies:
        if body.Name in modified:continue
        before=original[body.Name];after=body.Shape
        assert before.cut(after).Volume+after.cut(before).Volume<1e-6,body.Name
        old=original_global[body.Name];new=global_shape(body)
        assert old.cut(new).Volume+new.cut(old).Volume<1e-6,body.Name
        unchanged.append(body.Name)
    print('CHECKED unchanged bodies',len(unchanged),flush=True)
    sample_name='parking_tray_interface_Body'
    shapes={b.Name:global_shape(b) for b in all_bodies if b.Name!=sample_name}
    overlaps=[]
    for a,b in itertools.combinations(shapes,2):
        if not shapes[a].BoundBox.intersect(shapes[b].BoundBox):continue
        v=shapes[a].common(shapes[b]).Volume
        assert v<.01,(a,b,v)
        overlaps.append(dict(a=a,b=b,overlap_mm3=v))
    floors=[];contacts=[];lowering=[];tray_paths=[]
    sample=doc.getObject(sample_name).Shape
    width=evaluate(doc,'DeckWidth')
    for source,(floor,count) in FLOORS.items():
        body=doc.getObject(source+'_Body');base=source=='module_1'
        top=evaluate(doc,'BaseThickness' if base else 'DeckThickness')
        gap=evaluate(doc,'DeckEdgeGap') if base else 0
        origin=body.getGlobalPlacement().Base
        edges=bay_edges(count,width);widths=[b-a for a,b in zip(edges,edges[1:])]
        assert body.ParkingBays==body.TrayRecessCount==count
        assert body.GarageFloor==floor
        if count==2:assert abs(widths[0]-2*widths[1])<1e-6
        centers=[(evaluate(doc,center_x(count,i))+gap,evaluate(doc,'ParkingCenterY')+gap) for i in range(count)]
        sketch=next(o for o in body.Group if o.TypeId=='Sketcher::SketchObject' and o.Name.startswith('Sketch_ParkingTrayRecesses'))
        recess=Part.makeFace(sketch.Shape.Wires,'Part::FaceMakerBullseye')
        assert len(sketch.Shape.Wires)==count
        for wire,(x,y) in zip(sorted(sketch.Shape.Wires,key=lambda w:w.BoundBox.Center.x),centers):
            assert abs(wire.BoundBox.XLength-40.6)<1e-6
            assert abs(wire.BoundBox.YLength-84.6)<1e-6 # 80.6 mm foot + 4 mm finger opening
            assert abs(wire.BoundBox.Center.x-x)<1e-6
            assert abs(floor_height(body.Shape,x,y)-(top-1.6))<1e-6
        paint={}
        for color,mask in masks(body).items():
            assert abs(mask.BoundBox.ZMin-top)<1e-6
            assert mask.common(recess).Area<1e-6,(source,color)
            cut=evaluate(doc,'DeckBlueDepth' if color=='Blue' else 'DeckMarkingDepth')
            assert body.Shape.common(mask.extrude(App.Vector(0,0,-cut))).Volume<1e-5
            paint[color]=mask.Area
            for hx,hy in [('ColumnInset','ColumnInset'),('ColumnX2','ColumnInset'),('ColumnInset','ColumnY2'),('ColumnX2','ColumnY2')]:
                x=evaluate(doc,hx)-(0 if base else evaluate(doc,'DeckEdgeGap'))
                y=evaluate(doc,hy)-(0 if base else evaluate(doc,'DeckEdgeGap'))
                keep=Part.makeCylinder(11,.5,App.Vector(x,y,top-.5))
                assert mask.extrude(App.Vector(0,0,-cut)).common(keep).Volume<1e-6
        assert paint['White']>0 and paint['Yellow']>0
        assert ('Blue' in paint)==(count==2)
        floors.append(dict(floor=floor,part=source,bays=count,ids=[f'{floor}0{i+1}' for i in range(count)],
            bay_widths_mm=widths,accessible_bay='left' if count==2 else None,
            local_recess_centers_mm=centers,recess_footprint_mm=[40.6,80.6],
            recess_depth_mm=1.6,minimum_recess_floor_thickness_mm=top-1.6,
            paint_mask_areas_mm2=paint,decoration_outside_recess_floors=True))
        if not base:
            level=int(source.rsplit('_',1)[1])
            for i,(cx,cy) in enumerate([('ColumnInset','ColumnInset'),('ColumnX2','ColumnInset'),('ColumnInset','ColumnY2'),('ColumnX2','ColumnY2')],1):
                x=evaluate(doc,cx)-evaluate(doc,'DeckEdgeGap');y=evaluate(doc,cy)-evaluate(doc,'DeckEdgeGap')
                slab=Part.makeCylinder(10,.05,App.Vector(x,y,0))
                old_area=original[body.Name].common(slab).Volume/.05
                area=body.Shape.common(slab).Volume/.05
                assert abs(old_area-area)<1e-5
                contacts.append(dict(floor=floor,column=i,bearing_area_mm2=area,unchanged=True))
            fixed=[shapes[f'column_{i}_segment_{level}_Body'] for i in range(1,5)]
            fixed +=[shapes['module_1_Body'],shapes['module_2_Body']]
            for dz in (12,8,3,0):
                moved=shapes[body.Name].copy();moved.translate(App.Vector(0,0,dz))
                v=sum(moved.common(s).Volume for s in fixed)
                assert v<.01,(source,dz,v)
                lowering.append(dict(floor=floor,lift_mm=dz,overlap_mm3=v))
        for i,(x,y) in enumerate(centers,1):
            for dz,dy in [(0,0),(1.8,0),(1.8,-10),(1.8,-45),(1.8,-90)]:
                moved=sample.copy();moved.translate(App.Vector(origin.x+x,origin.y+y+dy,origin.z+top-1.6+dz))
                for name,fixed in shapes.items():
                    if moved.BoundBox.intersect(fixed.BoundBox):
                        v=moved.common(fixed).Volume
                        assert v<.01,(source,i,dz,dy,name,v)
                tray_paths.append(dict(floor=floor,bay=i,lift_mm=dz,front_translation_mm=dy,interference=False))
        if base:
            # All base changes must stay within the parking surface, clear of
            # the F dovetails, back wall and original column mounting pins.
            before=original[body.Name];after=body.Shape
            changed=before.cut(after).fuse(after.cut(before))
            region=Part.makeBox(195.8,145,8.01,App.Vector(.1,.1,0))
            assert changed.cut(region).Volume<1e-5
    old_bounds=Part.makeCompound([s for n,s in original_global.items() if n!=sample_name]).BoundBox
    bounds=Part.makeCompound(list(shapes.values())).BoundBox
    assert all(abs(a-b)<1e-6 for a,b in zip(
        [old_bounds.XMin,old_bounds.YMin,old_bounds.ZMin,old_bounds.XMax,old_bounds.YMax,old_bounds.ZMax],
        [bounds.XMin,bounds.YMin,bounds.ZMin,bounds.XMax,bounds.YMax,bounds.ZMax]))
    assert [row['bays'] for row in floors]==[2,2,3,3]
    assert sum(row['bays'] for row in floors)==10
    result.update(floors=floors,total_bays=10,unchanged_bodies=unchanged,assembly_overlap_checks=overlaps,
        collar_contacts=contacts,deck_lowering_paths=lowering,tray_removal_paths=tray_paths,
        source_outer_envelope_preserved=True,F_interfaces_and_signs_preserved=True,
        physical_fit_and_vehicle_wheel_restraints='not_verified')
    print('CHECKED four floors, 10 slots, supports and',len(tray_paths),'tray removal positions',flush=True)
    return result


def main():
    cad=ROOT/'garage-bookshelf-v4-assembly.FCStd'
    backup=ROOT/'backups/2026-10-25-before-four-floor-decoration.FCStd'
    report=ROOT/'reports/four-floor-decoration-validation.json'
    assert sha(cad)==EXPECTED_SHA256,'Formal CAD changed; inspect before applying.'
    if backup.exists():assert sha(backup)==EXPECTED_SHA256
    else:shutil.copy2(cad,backup)
    print_before=print_files()
    doc=App.openDocument(str(cad))
    original={b.Name:b.Shape.copy() for b in doc.Objects if b.TypeId=='PartDesign::Body'}
    original_global={b.Name:global_shape(b) for b in doc.Objects if b.TypeId=='PartDesign::Body'}
    retired={}
    for source,(floor,count) in FLOORS.items():
        body=doc.getObject(source+'_Body')
        retired[source]=retire_old_surface(body)
        add_recesses(body,count,base=source=='module_1')
        add_recessed(body,count,floor)
        print('UPDATED floor',floor,source,count,'bays',flush=True)
    result=verify(doc,original,original_global)
    snapshots={b.Name:b.Shape.copy() for b in doc.Objects if b.TypeId=='PartDesign::Body'}
    candidate=ROOT/'previews/parking-decoration-refresh/four-floor-candidate.FCStd'
    candidate.parent.mkdir(parents=True,exist_ok=True)
    doc.saveAs(str(candidate))
    from cad_view_style import preserve_views
    result['appearance']=preserve_views(backup,candidate,doc,[name+'_Body' for name in FLOORS])
    App.closeDocument(doc.Name)
    reopened=App.openDocument(str(candidate));valid(reopened)
    for name,before in snapshots.items():
        after=reopened.getObject(name).Shape
        assert before.cut(after).Volume+after.cut(before).Volume<1e-5,name
    App.closeDocument(reopened.Name)
    assert print_files()==print_before
    assert sha(cad)==EXPECTED_SHA256
    candidate.replace(cad)
    result.update(status='passed',source_sha256=EXPECTED_SHA256,cad_sha256=sha(cad),
        backup=str(backup),saved_reopened=True,retired_native_objects=retired,
        existing_print_files_unchanged=True,STEP_STL_3MF_ZIP_regenerated=False)
    report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print('PASS',report,flush=True)


if __name__=='__main__':main()
