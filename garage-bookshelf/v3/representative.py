"""Stage three gate: real production right deck, no added or simplified geometry."""
import sys,json
from pathlib import Path
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as App, Mesh, MeshPart
import parameters
from assembly import group,part
from components.shelves import build
ROOT=Path(__file__).resolve().parent

def run():
    if 'Representative' in App.listDocuments():App.closeDocument('Representative')
    d=App.newDocument('Representative');parameters.create(d)
    _,b=part(d,group(d,'Garage','代表性零件'),'garage_deck_1_right','停车层板1右',('DeckHalfWidth','Zero','DeckZ1'))
    build(b,True);d.recompute()
    before=b.Shape.Volume;old=b.Shape.optimalBoundingBox().ZLength
    parameters.set_value(d,'DeckThickness','6 mm')
    changed=b.Shape.optimalBoundingBox().ZLength
    assert abs(changed-old-1)<1e-7 and b.Shape.isValid()
    parameters.set_value(d,'DeckThickness','5 mm')
    assert abs(b.Shape.Volume-before)<1e-6
    sketches=[o for o in d.Objects if o.TypeId=='Sketcher::SketchObject']
    assert all(s.FullyConstrained for s in sketches)
    path=ROOT/'representative.FCStd';d.recompute();d.saveAs(str(path));App.closeDocument(d.Name)
    d=App.openDocument(str(path));d.recompute();b=d.getObject('garage_deck_1_right_Body');assert b.Shape.isValid() and len(b.Shape.Solids)==1
    m=MeshPart.meshFromShape(Shape=b.Shape,LinearDeflection=.02,AngularDeflection=.15,Relative=False)
    m.write(str(ROOT/'representative.stl'));r=Mesh.Mesh(str(ROOT/'representative.stl'));assert r.isSolid() and len(r.getSeparateComponents())==1
    result=dict(status='passed',part='garage_deck_1_right',sketches=len(sketches),all_fully_constrained=True,features=['PartDesign::Pad','PartDesign::Pocket','PartDesign::SubtractiveLoft'],thickness_before_mm=old,thickness_modified_mm=changed,restored_volume_mm3=b.Shape.Volume,save_close_reopen='passed',stl_closed=True,freecad_version=App.Version())
    (ROOT/'reports/03-representative-validation.json').write_text(json.dumps(result,indent=2))
    App.closeDocument(d.Name);print(json.dumps(result,indent=2));return result
if __name__=='__main__':run()
