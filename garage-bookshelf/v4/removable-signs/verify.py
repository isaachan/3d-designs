"""Check delivered project hashes, placement, native saved document and unchanged baseline."""
import sys,json,hashlib,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent
sys.path.insert(0,str(BASE));sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as A,Part
from assembly import global_shape
from check_package import project_bounds
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads((ROOT/'reports/validation.json').read_text());assert r['status']=='passed' and sha(BASE/'garage-bookshelf-v4-assembly.FCStd')==r['baseline_cad_sha256']
d=A.openDocument(str(ROOT/'removable-signs-assembly.FCStd'));d.recompute()
invalid=[(o.Name,o.getStatusString()) for o in d.Objects if any(s in o.State for s in ['Invalid','Error'])];assert not invalid,invalid
bs=[o for o in d.Objects if o.TypeId=='PartDesign::Body'];assert len(bs)==50
assert d.getObject('top_carrier_lower') is None and d.getObject('top_carrier_upper') is None
assert abs(d.top_carrier_Body.Shape.BoundBox.ZLength-58)<1e-5
# The former gap between rows is now continuous printable material.
seam=Part.makeBox(170,1,2,A.Vector(5,-1.5,28))
assert abs(d.top_carrier_Body.Shape.common(seam).Volume-340)<1e-5
assert all(b.Shape.isValid() and len(b.Shape.Solids)==1 for b in bs)
box=Part.makeCompound([global_shape(b) for b in bs]).optimalBoundingBox();dims=[box.XLength,box.YLength,box.ZLength]
assert all(abs(a-b)<1e-5 for a,b in zip(dims,[538,173.2,364])),dims
step=Part.Shape();step.read(str(ROOT/'removable-signs-assembly.step'));assert len(step.Solids)==50
slice_report=json.loads((ROOT/'reports/slicing.json').read_text());assert slice_report['status']=='passed' and len(slice_report['projects'])==6
placements=[]
for p in slice_report['projects']:
 file=ROOT/'bambu-projects'/(p['name']+'.3mf');assert sha(file)==p['project_sha256']
 assert all(sha(ROOT/'print-stl'/f)==h for f,h in p['source_sha256'].items())
 placements.append(dict(project=p['name'],bounds=project_bounds(file)))
assert [len(p['bounds']) for p in placements]==[1,1,1,1,2,2]
report=dict(status='passed',saved_cad_reopened=True,invalid_objects=invalid,assembly_dimensions_mm=dims,step_solids=50,projects=placements,baseline_preserved=True,top_lettering_on_one_continuous_carrier=True,cad_sha256=sha(ROOT/'removable-signs-assembly.FCStd'))
(ROOT/'reports/delivery-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('PASS saved native CAD, STEP, source hashes, 6 sliced projects and brim placement; baseline unchanged')
