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
    marking_sketches=[s for s in ss if 'ParkingMarkingColor' in s.PropertiesList]
    assert len(ss)==180+len(marking_sketches) and all(s.FullyConstrained for s in ss)
    assert all(any('ParkingMarkingColor' in s.PropertiesList for s in doc.getObject(f'garage_deck_{lev}_Body').Group) for lev in (1,2))
    assert not any("RootRib" in o.Name for o in doc.Objects)
    assert all(b.Shape.isValid() and len(b.Shape.Solids)==1 for b in bs)
    invalid=[(o.Name,list(o.State)) for o in doc.Objects if any(k in o.State for k in ['Invalid','Error'])]
    assert not invalid,invalid
    assert not any(o.TypeId in ['Part::Feature','Mesh::Feature','PartDesign::Feature'] for o in doc.Objects)
    return dict(bodies=len(bs),sketches=len(ss),parking_marking_sketches=len(marking_sketches),fully_constrained=True,single_solid_each=True,invalid_objects=invalid)


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
    assert all(abs(a-b)<1e-5 for a,b in zip(dims,[evaluate(doc,'OverallEnvelopeWidth'),170,364])),dims
    mb=Part.makeCompound([shapes[f'module_{i}_Body'] for i in (1,2,3)]).optimalBoundingBox()
    assert all(abs(a-b)<1e-5 for a,b in zip([mb.XLength,mb.YLength,mb.ZLength],[490,170,238]))
    # The former four triangular root gussets must leave the book opening clear.
    clear_region=Part.makeBox(evaluate(doc,'BookWidth-2*WallThickness')-.2,
        evaluate(doc,'BackFront')-1, evaluate(doc,'OverallHeight-BaseThickness')-.2,
        App.Vector(evaluate(doc,'GarageWidth+WallThickness')+.1,.1,evaluate(doc,'BaseThickness')+.1))
    book_overlap=sum(shapes[f'module_{i}_Body'].common(clear_region).Volume for i in (2,3))
    assert book_overlap<.001,book_overlap
    root_rib_removal=dict(removed_gussets=4,remaining_root_rib_features=0,
                         checked_opening_overlap_mm3=book_overlap)
    paths=[]
    for i in (1,2):
        a=shapes[f'module_{i}_Body'];b=shapes[f'module_{i+1}_Body']
        for offset in (30,15,5,1,0):
            s=b.copy();s.translate(App.Vector(offset,0,0));v=a.common(s).Volume
            assert v<.01,(i,offset,v)
            paths.append(dict(interface=i,positive_x_offset_mm=offset,overlap_mm3=v))
    # A deck is lowered onto its four supporting segments before the next four are installed.
    deck_paths=[];contacts=[];plain_decks=[]
    from build import CENTRES
    for lev in (1,2,3):
        plate=shapes[f'garage_deck_{lev}_Body'];z=evaluate(doc,f'DeckZ{lev}')
        local=doc.getObject(f'garage_deck_{lev}_Body').Shape
        box=local.optimalBoundingBox();thickness=evaluate(doc,'DeckThickness')
        assert abs(plate.BoundBox.XMin-evaluate(doc,'DeckEdgeGap'))<1e-6
        assert abs(evaluate(doc,'GarageWidth')-plate.BoundBox.XMax-evaluate(doc,'DeckEdgeGap+DeckRightTrim'))<1e-6
        holes=next(o for o in doc.getObject(f'garage_deck_{lev}_Body').Group if o.TypeId=='Sketcher::SketchObject' and o.Name.startswith('Sketch_FourLocatingHoles'))
        for circle,(x,y) in zip(holes.Geometry,CENTRES):
            assert abs(circle.Center.x+evaluate(doc,'DeckEdgeGap')-evaluate(doc,x))<1e-6
            assert abs(circle.Center.y+evaluate(doc,'DeckEdgeGap')-evaluate(doc,y))<1e-6
        assert abs(box.ZMin)<1e-6 and abs(box.ZMax-thickness)<1e-6
        expected=(evaluate(doc,'DeckWidth')*evaluate(doc,'DeckDepth')-4*3.141592653589793*evaluate(doc,'HoleRadius')**2)*thickness
        from parking_markings import check as check_parking
        parking=check_parking(doc.getObject(f'garage_deck_{lev}_Body'))
        assert abs(local.Volume-(expected-parking['removed_volume_mm3']))<1e-5
        assert not any('IntegralRibs' in feature.Name for feature in doc.getObject(f'garage_deck_{lev}_Body').Group)
        clearance=z-(evaluate(doc,'BaseThickness') if lev==1 else evaluate(doc,f'DeckZ{lev-1}')+thickness)
        assert abs(clearance-58)<1e-6
        plain_decks.append(dict(level=lev,dimensions_mm=[box.XLength,box.YLength,box.ZLength],extra_rib_height_mm=0,solid_volume_mm3=local.Volume,minimum_clear_height_below_mm=clearance,parking_layout=parking))
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
            full_area=3.141592653589793*(evaluate(doc,'CollarRadius')**2-evaluate(doc,'HoleRadius')**2)
            # Right trim clips a small cap of the right collars; retain >=99% bearing.
            outline=Part.makeBox(evaluate(doc,'DeckWidth'),evaluate(doc,'DeckDepth'),.05,App.Vector(evaluate(doc,'DeckEdgeGap'),evaluate(doc,'DeckEdgeGap'),z))
            target=slab.common(outline).Volume/.05-3.141592653589793*evaluate(doc,'HoleRadius')**2
            assert target/full_area>=.99,(lev,n,target,full_area)
            assert abs(area-target)<.01,(area,target)
            contacts.append(dict(level=lev,column=n,bearing_area_mm2=round(area,3),full_collar_bearing_fraction=area/full_area))
    # Explicitly check the two requested viewing/mounting directions.
    sign=shapes['book_depot_sign_Body'];sb=sign.optimalBoundingBox()
    assert abs(sb.YMin)<1e-5 and abs(sb.YLength-evaluate(doc,'SignMountDepth'))<1e-5
    assert abs(sb.XMin-evaluate(doc,'OverallWidth'))<1e-5
    assert abs(sb.XMax-evaluate(doc,'OverallEnvelopeWidth'))<1e-5
    front=[f for f in sign.Faces if abs(f.CenterOfMass.y)<1e-5 and f.normalAt(0,0).y<-.99]
    # Pocket openings can split the remaining front face (e.g. inside O and R).
    lettering=json.loads((ROOT/'reference/sign-lettering.json').read_text())
    assert doc.book_depot_sign_Body.EngravedSlogan==lettering['slogan']=='NO HORSEPOWER. ONLY BRAINPOWER.'
    assert lettering['rotation_degrees']==-90 and lettering['reading_direction']=='top_to_bottom'
    assert [row['text'] for row in lettering['lines']]==['NO HORSEPOWER.','ONLY BRAINPOWER.']
    engraved_area=0.;line_checks=[];previous_box=None
    for index,row in enumerate(lettering['lines'],1):
        profiles=[o for o in doc.book_depot_sign_Body.Group if o.TypeId=='Sketcher::SketchObject' and 'SignLine' in o.PropertiesList and o.SignLine==index]
        assert len(profiles)==len(row['glyphs'])
        face=Part.makeCompound([Part.makeFace(p.Shape.Wires,'Part::FaceMakerBullseye') for p in profiles])
        box=face.optimalBoundingBox();depth=evaluate(doc,'SignEngraveDepth')
        assert abs(box.YMin)<1e-6 and abs(box.YMax)<1e-6
        assert box.XMin>=4 and box.XMax<=evaluate(doc,'SignWidth')-4
        assert box.ZMin>4 and box.ZMax<evaluate(doc,'SignHeight')-4
        height=evaluate(doc,'SignTextHeight')
        assert abs(box.XLength-height)<1e-6
        assert abs(box.ZLength-row['width_per_cap_height']*height)<1e-6
        if previous_box is not None:
            assert abs(box.XMin-previous_box.XMax-evaluate(doc,'SignColumnGap'))<1e-6
            assert abs(box.ZMax-previous_box.ZMax)<1e-6
        previous_box=box
        cut=face.extrude(App.Vector(0,depth,0))
        assert doc.book_depot_sign_Body.Shape.common(cut).Volume<1e-5
        engraved_area+=face.Area
        line_checks.append(dict(text=row['text'],column_width_mm=box.XLength,vertical_length_mm=box.ZLength,left_x_mm=box.XMin,top_z_mm=box.ZMax))
    area=evaluate(doc,'SignWidth')*evaluate(doc,'SignHeight')
    assert abs(sum(f.Area for f in front)-(area-engraved_area))<1e-4
    expected_volume=area*evaluate(doc,'SignThickness')+evaluate(doc,'SignThickness')*(evaluate(doc,'SignMountDepth')-evaluate(doc,'SignThickness'))*evaluate(doc,'SignHeight')-engraved_area*depth
    assert abs(sign.Volume-expected_volume)<1e-4
    slogan_check=dict(text=lettering['slogan'],lines=line_checks,rotation_degrees=-90,reading_direction='top_to_bottom',engraved_depth_mm=depth,
                      remaining_back_thickness_mm=evaluate(doc,'SignThickness')-depth,
                      engraved_face_area_mm2=engraved_area,white_preview_means_optional_paint_fill=True,
                      one_piece_print=True)
    opening=Part.makeBox(evaluate(doc,'BookWidth-2*WallThickness'),evaluate(doc,'BackFront'),evaluate(doc,'OverallHeight-BaseThickness'),App.Vector(evaluate(doc,'GarageWidth+WallThickness'),0,evaluate(doc,'BaseThickness')))
    assert sign.common(opening).Volume<.001
    sign_mount_faces=[f for f in sign.Faces if abs(f.CenterOfMass.x-evaluate(doc,'OverallWidth'))<1e-5 and f.normalAt(0,0).x<-.99]
    wall_mount_faces=[f for f in shapes['module_3_Body'].Faces if abs(f.CenterOfMass.x-evaluate(doc,'OverallWidth'))<1e-5 and f.normalAt(0,0).x>.99]
    glue=sum(a.common(b).Area for a in sign_mount_faces for b in wall_mount_faces)
    assert abs(glue-evaluate(doc,'SignMountDepth')*evaluate(doc,'SignHeight'))<.001,glue
    mounting=[]
    for side,x in [('left','PostX1'),('right','PostX2')]:
        post=shapes['billboard_post_'+side+'_Body'];pb=post.optimalBoundingBox()
        assert abs(pb.YMin-evaluate(doc,'BackRear'))<1e-5
        assert abs(pb.YMax-evaluate(doc,'OverallDepth'))<1e-5
        assert abs(pb.ZMax-evaluate(doc,'BillboardBottom'))<1e-5
        strip=Part.makeBox(evaluate(doc,'PostWidth'),.05,evaluate(doc,'OverallHeight-PostBottom'),App.Vector(evaluate(doc,x),evaluate(doc,'BackRear'),evaluate(doc,'PostBottom')))
        area=post.common(strip).Volume/.05
        assert abs(area-evaluate(doc,'PostWidth')*evaluate(doc,'OverallHeight-PostBottom'))<.001
        mounting.append(dict(side=side,post_front_y_mm=pb.YMin,back_rear_y_mm=evaluate(doc,'BackRear'),post_rear_y_mm=pb.YMax,back_glue_contact_mm2=area))
    requested_orientation=dict(blue_sign_front_normal=[0,-1,0],blue_sign_front_y_mm=sb.YMin,blue_sign_x_range_mm=[sb.XMin,sb.XMax],blue_sign_excluded_from_main_body=True,main_body_width_mm=evaluate(doc,'OverallWidth'),book_opening_overlap_mm3=0,sign_to_right_outer_wall_contact_mm2=glue,posts_behind_back=mounting,deck_bracket_slots_removed=True,blue_sign_lettering=slogan_check)
    return dict(bounds_mm=[bb.XMin,bb.YMin,bb.ZMin,bb.XMax,bb.YMax,bb.ZMax],dimensions_mm=dims,main_body_dimensions_mm=[mb.XLength,mb.YLength,mb.ZLength],interfering_pairs=bad,book_root_rib_removal=root_rib_removal,requested_orientation=requested_orientation,module_insertion_paths=paths,deck_lowering_paths=deck_paths,collar_contact_areas=contacts,plain_parking_decks=plain_decks)


def parameter_test(doc):
    set_value(doc,'OverallDepth','172 mm')
    assert abs(doc.module_1_Body.Shape.BoundBox.YLength-172)<1e-5
    assert abs(doc.garage_deck_1_Body.Shape.BoundBox.YLength-160.6)<1e-5
    y=doc.column_3_segment_1.getGlobalPlacement().Base.y
    assert abs(y-147)<1e-5,y
    set_value(doc,'OverallDepth','170 mm')
    set_value(doc,'GarageWidth','202 mm')
    assert abs(doc.garage_deck_1_Body.Shape.BoundBox.XLength-evaluate(doc,'DeckWidth'))<1e-5
    assert abs(doc.module_2.getGlobalPlacement().Base.x-202)<1e-5
    assert abs(evaluate(doc,'BookModuleWidth')-144)<1e-5
    set_value(doc,'GarageWidth','200 mm')
    set_value(doc,'OverallWidth','500 mm')
    assert abs(evaluate(doc,'BookModuleWidth')-150)<1e-5
    assert abs(doc.book_depot_sign.getGlobalPlacement().Base.x-500)<1e-5
    assert abs(doc.module_3.getGlobalPlacement().Base.x-350)<1e-5
    set_value(doc,'OverallWidth','490 mm')
    set_value(doc,'SignWidth','52 mm')
    assert abs(doc.book_depot_sign_Body.Shape.BoundBox.XLength-52)<1e-5
    profiles=[o for o in doc.book_depot_sign_Body.Group if o.TypeId=='Sketcher::SketchObject' and 'SignLine' in o.PropertiesList and o.SignLine in (1,2)]
    assert abs(Part.makeCompound([p.Shape for p in profiles]).BoundBox.Center.x-26)<1e-6
    set_value(doc,'SignWidth','48 mm')
    native(doc)
    return dict(overall_width_490_to_500_to_490='passed',sign_48_to_52_to_48='passed',lettering_stays_centred=True,depth_170_to_172_to_170='passed',garage_200_to_202_to_200='passed',body_deck_columns_and_modules_follow=True)


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
            orient='5 mm 无梁整板，底面贴床，停车图案朝上（层板3空白）'
        elif name.startswith('billboard'):
            rotation=App.Rotation(App.Vector(1,0,0),90);orient='牌/文字/支架放平'
        elif name=='book_depot_sign':
            rotation=App.Rotation(App.Vector(1,0,0),90);orient='蓝牌正面大面贴床'
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
    step_file=ROOT/'garage-bookshelf-v4-assembly.step'
    Part.makeCompound(all_shapes).exportStep(str(step_file))
    step_file.write_text('\n'.join(line.rstrip() for line in step_file.read_text().splitlines())+'\n')
    step=Part.Shape()
    step.read(str(ROOT/'garage-bookshelf-v4-assembly.step'))
    bb=step.optimalBoundingBox()
    assert len(step.Solids)==46,len(step.Solids)
    assert all(abs(a-b)<.001 for a,b in zip([bb.XLength,bb.YLength,bb.ZLength],[evaluate(doc,'OverallEnvelopeWidth'),170,364])),str(bb)
    return records


def main():
    file=ROOT/'garage-bookshelf-v4-assembly.FCStd'
    doc=App.openDocument(str(file));doc.recompute()
    nr=native(doc);print('PASS native solids and sketches',nr,flush=True)
    a=assembly(doc);print('PASS assembly and engraved slogan',flush=True)
    p=parameter_test(doc);print('PASS parameter round-trips',flush=True)
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
