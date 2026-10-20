"""Stage-one cross-check: exact script design vs every existing STL, not just boxes."""
import sys,json
from pathlib import Path
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD, Mesh
from reference_shapes import shapes,ROOT,OLD
from measure import bounds as shape_bounds, mesh_volume
from analyze_reference import bounds

def run():
    records=[]
    for name,s in shapes().items():
        m=Mesh.Mesh(str(OLD/'stl'/f'{name}.stl'))
        delta=max(abs(a-b) for a,b in zip(bounds(s.optimalBoundingBox()),bounds(m.BoundBox)))
        volume=abs(s.Volume-mesh_volume(m))/s.Volume;area=abs(s.Area-m.Area)/s.Area
        passed=delta<.02 and volume<.0005 and area<.0005 and len(s.Solids)==len(m.getSeparateComponents())
        records.append(dict(name=name,status='passed' if passed else 'failed',bounds_max_delta_mm=delta,volume_relative_delta=volume,area_relative_delta=area,exact_volume_mm3=s.Volume,exact_area_mm2=s.Area,solids=len(s.Solids)))
    r=dict(status='passed' if all(x['status']=='passed' for x in records) else 'failed',tolerances=dict(bounds_mm=.02,relative_volume_and_area=.0005),parts=records)
    (ROOT/'reports/01-reference-crosscheck.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2));assert r['status']=='passed'
if __name__=='__main__':run()
