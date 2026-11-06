"""Build a measured four-wheel insert using the BMW Z4 E89 native CAD method.

Freeze outlines with system Python (--freeze-label); build with FreeCAD Python.
Generation is confined to a fresh v5/build/ directory. Existing models stay intact.
"""
import argparse
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import struct
import sys
import tempfile
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED

import _bootstrap
from garage_bookshelf.paths import CAD, PROFILES, ROOT, TMP, output_directory, read_json, sha, source_record, write_json
from garage_bookshelf.parking.artifacts import output_artifact, parking_stem


def freeze_label(spec_path):
    """Freeze Arial Bold outlines once; CAD generation needs no system font API."""
    spec = read_json(spec_path)
    parking_stem(spec.get('variant'), spec.get('revision'))
    from matplotlib.font_manager import FontProperties
    from matplotlib.textpath import TextPath
    font = Path('/System/Library/Fonts/Supplemental/Arial Bold.ttf')
    prop = FontProperties(fname=str(font))
    path = TextPath((0, 0), spec['model_label'], size=10, prop=prop)
    bounds = path.get_extents()
    cap_height = TextPath((0, 0), 'H', size=10, prop=prop).get_extents().height
    contours = []
    for polygon in path.to_polygons():
        if len(polygon)>1 and abs(polygon[0]-polygon[-1]).max()<1e-9:
            polygon=polygon[:-1]
        contours.append([[(float(x)-(bounds.xmin+bounds.xmax)/2)/cap_height,
                          (float(y)-bounds.ymin)/cap_height] for x,y in polygon])
    result = dict(text=spec['model_label'],font='Arial Bold',source_font_sha256=sha(font),
                  nominal_cap_height_mm=4,nominal_width_mm=bounds.width*4/cap_height,
                  nominal_height_mm=bounds.height*4/cap_height,contours_per_cap_height=contours)
    target=spec_path.with_name('model-label-outline.json')
    if target.exists():
        raise FileExistsError(target)
    write_json(target,result)
    print(target,flush=True)


if __name__=='__main__' and '--freeze-label' in sys.argv:
    parser=argparse.ArgumentParser()
    parser.add_argument('--freeze-label',type=Path,required=True)
    freeze_label(parser.parse_args().freeze_label)
    raise SystemExit(0)


def parse_build_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', type=Path, required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    args.spec_data = read_json(args.spec)
    try:
        parking_stem(args.spec_data.get('variant'), args.spec_data.get('revision'))
    except ValueError as error:
        parser.error(str(error))
    return args


if __name__ == '__main__':
    # Reject unsafe identifiers before importing the CAD runtime or creating output.
    build_args = parse_build_args()

sys.path.insert(0, '/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as App
import Part
import Sketcher
import Mesh
import MeshPart
from garage_bookshelf.geometry.sketches import plane, rectangle, loops
from garage_bookshelf.geometry.features import pad, finish
from garage_bookshelf.parking.recesses import rounded_profile, LAYOUTS, center_x
from garage_bookshelf.parameters import evaluate
from garage_bookshelf.printing.bambu import run_cli, read_settings
from garage_bookshelf.printing.threemf import project_bounds
from garage_bookshelf.rendering.software import triangles, render
from garage_bookshelf.appearance.storage import material_records, serialize_material_records


def build(spec, outline):
    doc = App.newDocument('MeasuredParkingTray')
    sheet = doc.addObject('Spreadsheet::Sheet', 'DesignParameters')
    for row, (name, value) in enumerate(dict(Zero=0, TrayFootWidth=40,
            TrayFootLength=80, TrayFootRadius=2, TrayPlateThickness=2,
            TrayTabWidth=10, TrayTabProjection=3, TrayGripRise=1.2).items(), 1):
        sheet.set('A'+str(row), name)
        sheet.set('B'+str(row), f'{value} mm')
        sheet.setAlias('B'+str(row), name)
    fit = doc.addObject('App::FeaturePython', 'WheelFit')
    measured = spec['measurements_mm']
    aliases = dict(Span='S', FrontOutside='Bf', RearOutside='Br',
                   FrontDiameter='Df', RearDiameter='Dr', FrontWidth='Tf', RearWidth='Tr')
    values = {name: measured[key] for name, key in aliases.items()}
    values.update(SideClearance=.2, RadialClearance=.15, GuideWall=1.2,
                  GuideHeight=1.6, CradleLength=10)
    for name, value in values.items():
        fit.addProperty('App::PropertyLength', name, 'Measurements' if name in (
            'Span', 'FrontOutside', 'RearOutside', 'FrontDiameter', 'RearDiameter',
            'FrontWidth', 'RearWidth') else 'Fit allowances')
        setattr(fit, name, value)
    for name, formula in dict(Wheelbase='Span-(FrontDiameter+RearDiameter)/2',
            FrontTrack='FrontOutside-FrontWidth', RearTrack='RearOutside-RearWidth').items():
        fit.addProperty('App::PropertyLength', name, 'Derived')
        fit.setExpression(name, formula)
    fit.addProperty('App::PropertyString', 'FitStatus')
    fit.FitStatus = 'Measured wheel geometry; gravity cradle; no snap lock; physical fit pending'
    body = doc.addObject('PartDesign::Body', 'measured_tray_Body')
    body.Label = spec['model_label'] + ' - measured four-wheel cradle'
    doc.recompute()
    sketch = plane(body, 'Sketch_RoundedFoot')
    rounded_profile(sketch, 'Zero', 'Zero', 'TrayFootWidth', 'TrayFootLength', 'TrayFootRadius')
    pad(body, 'Pad_Foot', sketch, 'TrayPlateThickness')
    for name, z, height in [('Tab', 'Zero', 'TrayPlateThickness'),
                            ('Grip', 'TrayPlateThickness', 'TrayGripRise')]:
        s = rectangle(body, 'Sketch_'+name, 'TrayTabWidth', 'TrayTabProjection+0.5 mm',
            origin=('-TrayTabWidth/2', '-TrayFootLength/2-TrayTabProjection'),
            offset=('Zero','Zero',z))
        pad(body, 'Pad_'+name, s, height)
    foot = body.Shape.copy()
    wheels = []
    polygons = []
    for end, axle in [('Front', 1), ('Rear', -1)]:
        for side in [-1, 1]:
            x = f'({side})*WheelFit.{end}Track/2'
            y = f'({axle})*WheelFit.Wheelbase/2'
            half = f'(WheelFit.{end}Width/2+WheelFit.SideClearance+WheelFit.GuideWall)'
            x0, x1 = f'({x})-({half})', f'({x})+({half})'
            y0, y1 = f'({y})-WheelFit.CradleLength/2', f'({y})+WheelFit.CradleLength/2'
            polygons.append([(x0,y0),(x1,y0),(x1,y1),(x0,y1)])
            wheels.append((end, side, x, y))
    s = loops(body, 'Sketch_FourCradleBlocks', polygons,
        offset=('Zero','Zero','TrayPlateThickness'))
    pad(body, 'Pad_FourCradleBlocks', s, 'WheelFit.GuideHeight')
    for end, side, x, y in wheels:
        # YZ plane normal points +X. A reversed pocket sweeps from the left
        # inner wall to the right inner wall, leaving 1.2 mm solid side walls.
        x0 = f'({x})-WheelFit.{end}Width/2-WheelFit.SideClearance'
        s = plane(body, f'Sketch_{end}_{side+1}_TireArc', orientation='YZ',
            offset=(x0,'Zero','Zero'))
        radius = f'WheelFit.{end}Diameter/2+WheelFit.RadialClearance'
        z = f'TrayPlateThickness+({radius})'
        i = s.addGeometry(Part.Circle(App.Vector(evaluate(doc,y),evaluate(doc,z),0),
            App.Vector(0,0,1),evaluate(doc,radius)),False)
        for kind, value in [('DistanceX',y),('DistanceY',z),('Radius',radius)]:
            args=(i,evaluate(doc,value)) if kind=='Radius' else (i,3,evaluate(doc,value))
            k=s.addConstraint(Sketcher.Constraint(kind,*args))
            from garage_bookshelf.parameters import expression
            s.setExpression(f'Constraints[{k}]',expression(value))
        p = body.newObject('PartDesign::Pocket', f'Pocket_{end}_{side+1}_TireArc')
        p.Profile=s
        p.setExpression('Length', f'WheelFit.{end}Width+2*WheelFit.SideClearance')
        p.Reversed=True
        p.Refine=True
        finish(body,p)
    # Frozen font outlines are normalized to cap height, so regeneration does
    # not depend on font installation or GUI font APIs. Every vertex remains
    # dimension-driven in a native sketch; the raised lettering is a native Pad.
    label=doc.addObject('App::FeaturePython','ModelLabel')
    label.addProperty('App::PropertyString','Text','Label')
    label.Text=outline['text']
    label.addProperty('App::PropertyString','Font','Label');label.Font=outline['font']
    for name,value in dict(CharacterHeight=spec.get('label_cap_height_mm',4),
                           RaisedHeight=.4,BottomY=-37.7).items():
        label.addProperty('App::PropertyLength' if name!='BottomY' else 'App::PropertyDistance',name,'Label')
        setattr(label,name,value)
    polygons=[[(f'ModelLabel.CharacterHeight*({x})',
                f'ModelLabel.BottomY+ModelLabel.CharacterHeight*({y})') for x,y in contour]
              for contour in outline['contours_per_cap_height']]
    s=loops(body,'Sketch_ModelLabel',polygons,offset=('Zero','Zero','TrayPlateThickness'))
    text_pad=pad(body,'Pad_ModelLabel',s,'ModelLabel.RaisedHeight')
    text_pad.Label=spec['model_label'] + ' · raised 0.4 mm'
    doc.recompute()
    assert all(s.FullyConstrained for s in doc.Objects if s.TypeId=='Sketcher::SketchObject')
    assert body.Shape.isValid() and len(body.Shape.Solids)==1
    assert abs(body.Shape.common(foot).Volume-foot.Volume)<1e-6
    for end,side,x,y in wheels:
        d=getattr(fit,end+'Diameter').Value
        tire=Part.makeCylinder(d/2,getattr(fit,end+'Width').Value,
            App.Vector(evaluate(doc,x)-getattr(fit,end+'Width').Value/2,evaluate(doc,y),2+d/2),App.Vector(1,0,0))
        assert body.Shape.common(tire).Volume<1e-6
        raised=tire.copy();raised.translate(App.Vector(0,0,2))
        assert body.Shape.common(raised).Volume<1e-6
    return doc,body,foot


def save_views(path, doc, body):
    # Clone only saved native view providers; geometry remains native Pad/Pocket.
    with ZipFile(CAD) as z:
        source={n:z.read(n) for n in z.namelist()}
    root=ET.fromstring(source['GuiDocument.xml'])
    data=root.find('ViewProviderData')
    providers={e.attrib['name']:e for e in data}
    type_templates={'Spreadsheet::Sheet':'DesignParameters',
        'PartDesign::Body':'parking_tray_interface_Body',
        'Sketcher::SketchObject':'Sketch_TrayFoot',
        'PartDesign::Pad':'Pad_TrayFoot', 'PartDesign::Pocket':'Pocket_FourLocatingHoles'}
    data.clear()
    appearance = next(p for p in providers['parking_tray_interface_Body'].iter('Property')
        if p.attrib.get('name')=='ShapeAppearance')[0].attrib['file']
    record = material_records(source[appearance])[0]
    source['MeasuredMaterial.bin']=serialize_material_records([record]*len(body.Shape.Faces))
    for obj in doc.Objects:
        if obj.TypeId not in type_templates: continue
        vp=copy.deepcopy(providers[type_templates[obj.TypeId]])
        vp.set('name',obj.Name)
        for prop in vp.iter('Property'):
            if prop.attrib.get('name')=='Visibility':
                prop[0].set('value','true' if obj in [body,body.Tip] else 'false')
            if prop.attrib.get('name') in ('LineColorArray','PointColorArray'):
                prop[0].set('file','MeasuredEmpty.bin')
            if prop.attrib.get('name')=='ShapeAppearance' and obj in [body,body.Tip]:
                prop[0].set('file','MeasuredMaterial.bin')
        data.append(vp)
    data.set('Count',str(len(data)))
    rotation=App.Rotation(App.Vector(.98427719,-.17521913,.022297541),63.004)
    camera_position=App.Vector(0,-1.5,1.8)+rotation.multVec(App.Vector(0,0,150))
    root.find('Camera').set('settings', 'OrthographicCamera {\n'
        f' position {camera_position.x} {camera_position.y} {camera_position.z}\n'
        ' orientation 0.98427719 -0.17521913 0.022297541 1.0996453\n'
        ' nearDistance 1\n farDistance 1000\n aspectRatio 1\n focalDistance 150\n height 100\n}\n')
    source['MeasuredEmpty.bin']=struct.pack('<I',0)
    referenced={e.attrib['file'] for e in root.iter() if 'file' in e.attrib}
    with ZipFile(path) as z: result={n:z.read(n) for n in z.namelist()}
    result.update({n:source[n] for n in referenced})
    result['GuiDocument.xml']=ET.tostring(root,encoding='utf-8',xml_declaration=True)
    with ZipFile(path,'w',ZIP_DEFLATED) as z:
        for name,raw in result.items():z.writestr(name,raw)


def measured_tires(doc, shape):
    records=[]
    fit=doc.WheelFit
    for end, axle in [('Front',1),('Rear',-1)]:
        diameter=getattr(fit,end+'Diameter').Value
        width=getattr(fit,end+'Width').Value
        for side in (-1,1):
            x=side*getattr(fit,end+'Track').Value/2
            y=axle*fit.Wheelbase.Value/2
            tire=Part.makeCylinder(diameter/2,width,
                App.Vector(x-width/2,y,2+diameter/2),App.Vector(1,0,0))
            overlaps=[]
            for lift in (0,2):
                moved=tire.copy();moved.translate(App.Vector(0,0,lift))
                overlap=shape.common(moved).Volume
                assert overlap<1e-6,(end,side,lift,overlap)
                overlaps.append(dict(lift_mm=lift,overlap_mm3=overlap))
            records.append(dict(axle=end,side=side,center_mm=[x,y,2+diameter/2],
                                diameter_mm=diameter,width_mm=width,checks=overlaps))
    return records


def parameter_roundtrip(doc, original):
    fit=doc.WheelFit
    increments=dict(Span=.8,FrontOutside=.4,RearOutside=.3,FrontDiameter=.1,
                    RearDiameter=.2,FrontWidth=.1,RearWidth=.1)
    before={name:getattr(fit,name).Value for name in increments}
    for name,increment in increments.items():
        setattr(fit,name,before[name]+increment)
    doc.recompute()
    changed={name:getattr(fit,name).Value for name in increments}
    expected=dict(Wheelbase=changed['Span']-(changed['FrontDiameter']+changed['RearDiameter'])/2,
                  FrontTrack=changed['FrontOutside']-changed['FrontWidth'],
                  RearTrack=changed['RearOutside']-changed['RearWidth'])
    assert doc.measured_tray_Body.Shape.isValid()
    assert len(doc.measured_tray_Body.Shape.Solids)==1
    for name,value in expected.items():
        assert abs(getattr(fit,name).Value-value)<1e-6,(name,value)
    changed_tires=measured_tires(doc,doc.measured_tray_Body.Shape)
    for name,value in before.items():
        setattr(fit,name,value)
    doc.recompute()
    restored=doc.measured_tray_Body.Shape
    difference=[original.cut(restored).Volume,restored.cut(original).Volume]
    assert max(difference)<1e-6,difference
    assert abs(restored.Volume-original.Volume)<1e-6
    assert all(o.FullyConstrained for o in doc.Objects if o.TypeId=='Sketcher::SketchObject')
    return dict(input_before_mm=before,input_changed_mm=changed,derived_changed_mm=expected,
                changed_tires=changed_tires,restored_symmetric_difference_mm3=difference)


def main(args=None):
    args = args if args is not None else parse_build_args()
    spec = args.spec_data
    stem = parking_stem(spec.get('variant'), spec.get('revision'))
    outline_path=args.spec.with_name('model-label-outline.json')
    outline=read_json(outline_path)
    label_height=spec.get('label_cap_height_mm',4)
    assert isinstance(label_height,(int,float)) and 0<label_height<=4
    label_width=outline['nominal_width_mm']*label_height/outline['nominal_cap_height_mm']
    assert label_width<=36,'Reduce label_cap_height_mm to keep the full model name inside the plate'
    measurements=spec['measurements_mm']
    assert set(measurements)=={'S','Bf','Br','Df','Dr','Tf','Tr'}
    assert all(isinstance(v,(float,int)) and v>0 for v in measurements.values())
    assert measurements['S']>(measurements['Df']+measurements['Dr'])/2
    assert measurements['Bf']>measurements['Tf'] and measurements['Br']>measurements['Tr']
    assert spec['interface']=='parking-base-v1' and outline['text']==spec['model_label']
    photo=ROOT/spec['measurement_source']['path']
    assert sha(photo)==spec['measurement_source']['sha256']
    out=output_directory(args.output)
    cad = output_artifact(out, stem + '.FCStd')
    project = output_artifact(out, stem + '.3mf')
    stl = output_artifact(out, Path('evidence') / (stem + '.stl'))
    evidence=out/'evidence';evidence.mkdir()
    profiles=evidence/'profiles';profiles.mkdir()
    write_json(out/'measurements.json',spec)
    write_json(out/'model-label-outline.json',outline)
    (evidence/'make_parking_insert.py').write_bytes(Path(__file__).read_bytes())
    for name in ('X2D-0.4-standard-machine.json','PLA-0.20-process.json','PLA-black.json'):
        (profiles/name).write_bytes((PROFILES/name).read_bytes())
    before=sha(CAD)
    doc,body,foot=build(spec,outline)
    shape=body.Shape.copy()
    assert shape.BoundBox.XLength<=40+1e-6 and shape.BoundBox.YLength<=83+1e-6
    letters=shape.cut(doc.Pocket_Rear_2_TireArc.Shape)
    assert letters.Volume>0 and abs(letters.BoundBox.ZLength-.4)<1e-6
    lowered=letters.copy();lowered.translate(App.Vector(0,0,-.4))
    unsupported=lowered.cut(foot).Volume
    guide_overlap=letters.common(doc.Pocket_Rear_2_TireArc.Shape.cut(foot)).Volume
    assert unsupported<1e-6 and guide_overlap<1e-6
    label_check=dict(supported_by_foot=True,unsupported_volume_mm3=unsupported,
                     guide_overlap_mm3=guide_overlap,
                     dimensions_mm=[letters.BoundBox.XLength,letters.BoundBox.YLength,letters.BoundBox.ZLength])
    tire_checks=measured_tires(doc,shape)
    source=App.openDocument(str(CAD))
    base_difference=[source.parking_tray_interface_Body.Shape.cut(foot).Volume,
                     foot.cut(source.parking_tray_interface_Body.Shape).Volume]
    assert max(base_difference)<1e-6
    fit_checks=[]
    for name,count in LAYOUTS.items():
        shift='DeckEdgeGap+' if name=='module_1' else ''
        floor=('BaseThickness' if name=='module_1' else 'DeckThickness')+'-ParkingRecessDepth'
        for index in range(count):
            moved=shape.copy()
            moved.translate(App.Vector(evaluate(source,shift+center_x(count,index)),
                evaluate(source,shift+'ParkingCenterY'),evaluate(source,floor)))
            overlap=source.getObject(name+'_Body').Shape.common(moved).Volume
            assert overlap<.001,(name,index,overlap)
            fit_checks.append(dict(floor=name,index=index,overlap_mm3=overlap))
    assert len(fit_checks)==10
    App.closeDocument(source.Name)
    doc.saveAs(str(cad));save_views(cad,doc,body)
    points,colors=triangles(doc,{body.Tip.Name:[(.38,.43,.49)]},['measured_tray'],local=True)
    render(points,colors,out/'tray-preview.png',[-1.1,-1.65,2.4],width=1400,height=1100)
    render(points,colors,out/'top-preview.png',[0,-.001,1],width=1000,height=1400)
    mesh=MeshPart.meshFromShape(Shape=shape,LinearDeflection=.015,AngularDeflection=.08,Relative=False)
    bb=mesh.BoundBox;mesh.translate(-bb.XMin,-bb.YMin,-bb.ZMin)
    mesh.write(str(stl));check=Mesh.Mesh(str(stl))
    mesh_error=abs(abs(check.Volume)-shape.Volume)/shape.Volume
    assert check.isSolid() and not check.hasNonManifolds() and len(check.getSeparateComponents())==1
    assert mesh_error<.001
    App.closeDocument(doc.Name)
    reopened=App.openDocument(str(cad));reopened.recompute()
    assert reopened.measured_tray_Body.Shape.isValid()
    assert len(reopened.measured_tray_Body.Shape.Solids)==1
    assert abs(reopened.measured_tray_Body.Shape.Volume-shape.Volume)<1e-6
    assert max(shape.cut(reopened.measured_tray_Body.Shape).Volume,
               reopened.measured_tray_Body.Shape.cut(shape).Volume)<1e-6
    assert all(o.FullyConstrained for o in reopened.Objects if o.TypeId=='Sketcher::SketchObject')
    roundtrip=parameter_roundtrip(reopened,shape)
    fit=reopened.WheelFit
    derived=dict(wheelbase_mm=fit.Wheelbase.Value,front_track_mm=fit.FrontTrack.Value,
                 rear_track_mm=fit.RearTrack.Value)
    native_sketches=sum(o.TypeId=='Sketcher::SketchObject' for o in reopened.Objects)
    App.closeDocument(reopened.Name)
    print('PASS native CAD, seven-input roundtrip, four tires and ten bays:',stem,flush=True)
    TMP.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=stem+'-',dir=TMP) as temporary:
        scratch=Path(temporary)
        run_cli(['--load-settings',f'{profiles}/X2D-0.4-standard-machine.json;{profiles}/PLA-0.20-process.json',
                 '--load-filaments',profiles/'PLA-black.json','--orient','0','--arrange','1',
                 '--export-3mf',project,stl],scratch/'configure',evidence/'export.log')
        settings=read_settings(project,'black',False)
        bounds=project_bounds(project);assert len(bounds)==1
        actual=[hi-lo for lo,hi in zip(bounds[0]['min_mm'],bounds[0]['max_mm'])]
        expected=[shape.BoundBox.XLength,shape.BoundBox.YLength,shape.BoundBox.ZLength]
        assert all(abs(a-b)<.002 for a,b in zip(actual,expected)),(actual,expected)
        with ZipFile(project) as archive:
            assert not any(name.endswith('.gcode') for name in archive.namelist())
            (out/'plate-preview.png').write_bytes(archive.read('Metadata/plate_1.png'))
        sliced=scratch/'sliced';sliced.mkdir()
        run_cli(['--orient','0','--arrange','0','--outputdir',sliced,'--slice','0',project],
                scratch/'reload',evidence/'slice.log')
        result=read_json(sliced/'result.json');write_json(out/'slice-result.json',result)
        assert result['return_code']==0 and len(result['sliced_plates'])==1
        plate=result['sliced_plates'][0]
        assert len(plate['objects'])==1 and not plate['warning_message'],plate
    assert sha(CAD)==before
    artifacts=[cad,project,out/'measurements.json',out/'model-label-outline.json',
               out/'tray-preview.png',out/'top-preview.png',out/'plate-preview.png',
               out/'slice-result.json',*sorted(p for p in evidence.rglob('*') if p.is_file())]
    report=dict(source_record(),status='passed',validation_executed_at=datetime.now(timezone.utc).isoformat(),
        variant=spec['variant'],revision=spec['revision'],model_label=spec['model_label'],
        interface=spec['interface'],design_method='bmw-z4-e89-measured-wheel-cradle-v1',
        measurements_mm=measurements,measurement_source=spec['measurement_source'],**derived,
        side_clearance_mm=.2,radial_clearance_mm=.15,guide_wall_mm=1.2,guide_height_mm=1.6,
        front_slot_width_mm=measurements['Tf']+.4,rear_slot_width_mm=measurements['Tr']+.4,
        dimensions_mm=expected,volume_mm3=shape.Volume,
        native_sketches_fully_constrained=True,native_sketch_count=native_sketches,
        saved_reopened_recomputed=True,single_native_body=True,parameter_roundtrip=roundtrip,
        tire_clearances=tire_checks,base_symmetric_difference_mm3=base_difference,
        slot_fit_checks=fit_checks,formal_cad_unchanged=True,
        mesh_watertight=True,mesh_components=1,mesh_triangles=check.CountFacets,
        mesh_relative_volume_error=mesh_error,print_dimensions_mm=actual,
        model_label_geometry=dict(font=outline['font'],cap_height_mm=label_height,raised_height_mm=.4,
                                  width_mm=label_width,bottom_y_mm=-37.7,geometry_check=label_check),
        settings=settings,saved_project_reopened_and_sliced=True,warning_messages=plate['warning_message'],
        estimated_seconds=plate['total_predication'],
        estimated_filament_g=sum(f['total_used_g'] for f in plate['filaments']),
        actual_vehicle_body_and_chassis_clearance_verified=False,
        physical_fit_tested=False,vertical_lock=False,gcode_delivered=False,
        files={p.name:sha(p) for p in artifacts},
        artifact_locations={p.name:str(p.relative_to(ROOT)) for p in artifacts})
    write_json(out/'validation.json',report)
    print('PASS saved 3MF independently reopened and sliced:',project,
          'seconds',report['estimated_seconds'],'grams',report['estimated_filament_g'],flush=True)


if __name__=='__main__':
    main(build_args)

