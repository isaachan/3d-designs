"""Generate a new candidate under build/. Run with FreeCAD bundled Python."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import sys
import _bootstrap
from _bootstrap import ROOT

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    out=Path(args.output).resolve()
    if not out.is_relative_to(ROOT/'build') or out==(ROOT/'build') or out.exists():
        parser.error('Output must be a NEW directory strictly below music-card-box/build/.')
    out.mkdir(parents=True)
    import FreeCAD as App
    import FreeCADGui as Gui
    import Import
    import Part
    from music_card_box.model import build
    from music_card_box.artifacts import write_json,sha,mesh_data,export_3mf,print_vertices
    from music_card_box.validation import validate
    Gui.showMainWindow()
    # Save native view providers without asking Qt's offscreen backend to draw OpenGL.
    Gui.getMainWindow().setUpdatesEnabled(False)
    Gui.getMainWindow().hide()
    spec=json.loads((ROOT/'assets/design.json').read_text())
    doc,parts=build(spec)
    report=validate(doc,parts,spec)
    if Gui.activeDocument():
        Gui.activeDocument().activeView().viewAxonometric()
        Gui.activeDocument().activeView().fitAll()
    cad=out/'music-card-box-r1.FCStd'
    doc.recompute(); doc.saveAs(str(cad))
    # Verify that the saved CAD reopens and retains all native solids.
    App.closeDocument(doc.Name)
    # Hidden/offscreen documents have no active viewport. Store a useful
    # camera explicitly in GUI metadata; native model data is unchanged.
    from zipfile import ZipFile,ZIP_DEFLATED
    import xml.etree.ElementTree as ET
    import math
    direction=App.Vector(2.8,6.5,2.7);direction.normalize()
    right=App.Vector(0,0,1).cross(direction);right.normalize()
    up=direction.cross(right)
    matrix=App.Matrix()
    for col,vector in enumerate([right,up,direction],1):
        for row,c in enumerate(vector,1):setattr(matrix,f'A{row}{col}',c)
    rotation=App.Rotation(matrix);axis=rotation.Axis
    position=App.Vector(0,18,52)+direction*400
    with ZipFile(cad) as z:saved={n:z.read(n) for n in z.namelist()}
    gui=ET.fromstring(saved['GuiDocument.xml'])
    gui.find('Camera').set('settings','OrthographicCamera {\n'
        f' position {position.x} {position.y} {position.z}\n'
        f' orientation {axis.x} {axis.y} {axis.z} {rotation.Angle}\n'
        ' nearDistance 1\n farDistance 1000\n aspectRatio 1.4\n focalDistance 400\n height 150\n}\n')
    saved['GuiDocument.xml']=ET.tostring(gui,encoding='utf-8',xml_declaration=True)
    with ZipFile(cad,'w',ZIP_DEFLATED) as z:
        for name,raw in saved.items():z.writestr(name,raw)
    doc=App.openDocument(str(cad)); doc.recompute()
    parts={name:doc.getObject(name) for name in spec['print_parts']}
    second=validate(doc,parts,spec)
    for name in parts:
        assert abs(second['parts'][name]['volume_mm3']-report['parts'][name]['volume_mm3'])<1e-4,name
        assert all(abs(a-b)<1e-5 for a,b in zip(second['parts'][name]['bounds_mm'],report['parts'][name]['bounds_mm'])),name
    report['parts']=second['parts']
    report['checks']['saved_cad_reopened']=True
    Import.export(list(parts.values()),str(out/'music-card-box-r1.step'))
    raw=[]; printing=[]
    p=spec['dimensions_mm']; depth=p['InnerDepth']+2*p['Wall']
    for name,b in parts.items():
        mesh,vertices,faces=mesh_data(b.Shape)
        assert mesh.isSolid(),name
        raw.append({'name':name,'color':b.PrintColor,'vertices':vertices,'faces':faces})
        vertices=print_vertices(vertices,name,depth,p['Wall'],p['GlueGap'],p['PanelThickness'])
        triangles=[[vertices[i] for i in face] for face in faces]
        import Mesh
        print_mesh=Mesh.Mesh(triangles)
        print_mesh.write(str(out/(name+'.stl')))
        assert print_mesh.isSolid() and abs(print_mesh.BoundBox.ZMin)<1e-5,name
        assert print_mesh.BoundBox.XMin>=0 and print_mesh.BoundBox.YMin>=0 and print_mesh.BoundBox.XMax<220 and print_mesh.BoundBox.YMax<220
        printing.append({'name':name,'color':b.PrintColor,'vertices':vertices,'faces':faces})
        report['parts'][name]['mesh_closed']=True
        report['parts'][name]['triangles']=len(faces)
        report['parts'][name]['print_bounds_mm']=[print_mesh.BoundBox.XMin,print_mesh.BoundBox.YMin,print_mesh.BoundBox.ZMin,print_mesh.BoundBox.XMax,print_mesh.BoundBox.YMax,print_mesh.BoundBox.ZMax]
    for i,color in enumerate(spec['colors'],1):
        export_3mf(out/f'{i:02d}-{color}.3mf',[obj for obj in printing if obj['color']==color],spec['colors'])
    export_3mf(out/'music-card-box-assembly.3mf',raw,spec['colors'])
    write_json(out/'scene.json',{'spec':spec,'objects':raw})
    write_json(out/'design-snapshot.json',spec)
    report.update({'revision':spec['revision'],'validated_at':datetime.now(timezone.utc).isoformat(),
        'cad_sha256':sha(cad),'spec_sha256':sha(ROOT/'assets/design.json'),
        'tool_sha256':{str(f.relative_to(ROOT)):sha(f) for f in sorted(list((ROOT/'src/music_card_box').glob('*.py'))+[ROOT/'tools/build.py',ROOT/'tools/_bootstrap.py'])},
        'native_freecad_version':list(App.Version()),'artifact_locations':{}})
    files={f.name:sha(f) for f in out.iterdir() if f.suffix in ['.FCStd','.step','.stl','.3mf','.json']}
    report['files']=files
    write_json(out/'validation.json',report)
    sys.__stdout__.write('PASS '+str(out)+'\n');sys.__stdout__.flush()

if __name__=='__main__':
    # Qt offscreen on macOS can fault while unloading Coin3D. All work is
    # synchronously saved and verified above; exit without GUI teardown.
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc(); sys.stdout.flush(); sys.stderr.flush(); os._exit(1)
    sys.stdout.flush(); sys.stderr.flush(); os._exit(0)
