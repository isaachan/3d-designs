"""Measured four-wheel gravity cradle, editable native FreeCAD and Bambu project.

Run with FreeCAD's Python; --output must be a fresh subdirectory of v5/build/.
No assembly or existing print projects are modified.
"""
import copy
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / 'src'))
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
from garage_bookshelf.paths import CAD, PROFILES, TMP, study_directory
from garage_bookshelf.printing.bambu import run_cli, read_settings
from garage_bookshelf.printing.threemf import project_bounds
from garage_bookshelf.rendering.software import triangles, render
from garage_bookshelf.appearance.storage import material_records, serialize_material_records

OUT = study_directory('measured-tray-s51-b23-d10-t5p1')
STEM = 'parking-tray-s51-b23-d10-t5p1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    doc = App.newDocument('MeasuredParkingTray')
    sheet = doc.addObject('Spreadsheet::Sheet', 'DesignParameters')
    for row, (name, value) in enumerate(dict(Zero=0, TrayFootWidth=40,
            TrayFootLength=80, TrayFootRadius=2, TrayPlateThickness=2,
            TrayTabWidth=10, TrayTabProjection=3, TrayGripRise=1.2).items(), 1):
        sheet.set('A'+str(row), name)
        sheet.set('B'+str(row), f'{value} mm')
        sheet.setAlias('B'+str(row), name)
    fit = doc.addObject('App::FeaturePython', 'WheelFit')
    for name, value in dict(Span=51, FrontOutside=23, RearOutside=23,
            FrontDiameter=10, RearDiameter=10, FrontWidth=5.1, RearWidth=5.1,
            SideClearance=.2, RadialClearance=.15, GuideWall=1.2,
            GuideHeight=1.6, CradleLength=10).items():
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
    body.Label = 'Measured parking tray - S51 B23 D10 T5.1'
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


def main():
    original_hash=sha(CAD)
    doc,body,foot=build()
    shape=body.Shape.copy()
    source=App.openDocument(str(CAD))
    assert source.parking_tray_interface_Body.Shape.cut(foot).Volume<1e-6
    assert foot.cut(source.parking_tray_interface_Body.Shape).Volume<1e-6
    fit_checks=[]
    for name,count in LAYOUTS.items():
        shift='DeckEdgeGap+' if name=='module_1' else ''
        floor=('BaseThickness' if name=='module_1' else 'DeckThickness')+'-ParkingRecessDepth'
        for index in range(count):
            moved=shape.copy()
            moved.translate(App.Vector(evaluate(source,shift+center_x(count,index)),
                evaluate(source,shift+'ParkingCenterY'),evaluate(source,floor)))
            overlap=source.getObject(name+'_Body').Shape.common(moved).Volume
            assert overlap<.001
            fit_checks.append(dict(floor=name,index=index,overlap_mm3=overlap))
    App.closeDocument(source.Name)
    cad=OUT/(STEM+'.FCStd');doc.saveAs(str(cad));save_views(cad,doc,body)
    points,colors=triangles(doc,{body.Tip.Name:[(.38,.43,.49)]},['measured_tray'],local=True)
    render(points,colors,OUT/'tray-preview.png',[-1.1,-1.65,2.4],width=1400,height=1100)
    mesh=MeshPart.meshFromShape(Shape=shape,LinearDeflection=.015,AngularDeflection=.08,Relative=False)
    bb=mesh.BoundBox;mesh.translate(-bb.XMin,-bb.YMin,-bb.ZMin)
    stl=OUT/(STEM+'.stl');mesh.write(str(stl));check=Mesh.Mesh(str(stl))
    assert check.isSolid() and not check.hasNonManifolds() and len(check.getSeparateComponents())==1
    assert abs(abs(check.Volume)-shape.Volume)/shape.Volume<.001
    App.closeDocument(doc.Name)
    reopened=App.openDocument(str(cad));reopened.recompute()
    assert reopened.measured_tray_Body.Shape.isValid()
    assert abs(reopened.measured_tray_Body.Shape.Volume-shape.Volume)<1e-6
    assert all(s.FullyConstrained for s in reopened.Objects if s.TypeId=='Sketcher::SketchObject')
    reopened.WheelFit.Span=52
    reopened.WheelFit.FrontOutside=24
    reopened.recompute()
    assert reopened.measured_tray_Body.Shape.isValid()
    assert abs(reopened.WheelFit.Wheelbase.Value-42)<1e-6
    assert abs(reopened.WheelFit.FrontTrack.Value-18.9)<1e-6
    reopened.WheelFit.Span=51
    reopened.WheelFit.FrontOutside=23
    reopened.recompute()
    assert abs(reopened.measured_tray_Body.Shape.Volume-shape.Volume)<1e-6
    App.closeDocument(reopened.Name)
    print('PASS native CAD, four measured tire clearances, unchanged standard foot and all receiving slots',flush=True)
    project=OUT/(STEM+'.3mf');TMP.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='measured-tray-',dir=TMP) as scratch:
        work=Path(scratch)
        run_cli(['--load-settings',f'{PROFILES}/X2D-0.4-standard-machine.json;{PROFILES}/PLA-0.20-process.json',
            '--load-filaments',PROFILES/'PLA-black.json','--orient','0','--arrange','1',
            '--export-3mf',project,stl],work/'export-state',OUT/'export.log')
        settings=read_settings(project,'black',False)
        bounds=project_bounds(project);assert len(bounds)==1
        expected=[40,83,3.6]
        actual=[b-a for a,b in zip(bounds[0]['min_mm'],bounds[0]['max_mm'])]
        assert all(abs(a-b)<.002 for a,b in zip(sorted(actual),sorted(expected)))
        sliced=work/'sliced';sliced.mkdir()
        run_cli(['--orient','0','--arrange','0','--outputdir',sliced,'--slice','0',project],
            work/'reload-state',OUT/'slice.log')
        result=json.loads((sliced/'result.json').read_text())
        (OUT/'slice-result.json').write_text(json.dumps(result,indent=2)+'\n')
        assert result['return_code']==0 and len(result['sliced_plates'])==1
        plate=result['sliced_plates'][0]
        assert len(plate['objects'])==1 and not plate['warning_message']
    assert sha(CAD)==original_hash
    report=dict(status='passed',measurements_mm=dict(S=51,Bf=23,Br=23,Df=10,Dr=10,Tf=5.1,Tr=5.1),
        wheelbase_mm=41,front_track_mm=17.9,rear_track_mm=17.9,
        side_clearance_mm=.2,radial_clearance_mm=.15,guide_height_mm=1.6,
        slot_width_mm=5.5,dimensions_mm=[40,83,3.6],native_sketches_fully_constrained=True,
        parameter_roundtrip_passed=True,
        mesh_watertight=True,mesh_components=1,triangles=check.CountFacets,
        volume_mm3=shape.Volume,base_matches_current_standard=True,
        vehicle_tires_interference_mm3=0,slot_fit_checks=fit_checks,
        formal_cad_unchanged=True,formal_cad_sha256=original_hash,
        physical_fit_tested=False,vertical_lock=False,settings=settings,
        reopened_and_sliced=True,slicing_warnings=plate['warning_message'],
        estimated_seconds=plate['total_predication'],estimated_filament_g=plate['filaments'][0]['total_used_g'],
        sha256={p.name:sha(p) for p in (cad,stl,project)})
    (OUT/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(output=str(OUT),seconds=report['estimated_seconds'],grams=report['estimated_filament_g'])),flush=True)


if __name__=='__main__':main()
