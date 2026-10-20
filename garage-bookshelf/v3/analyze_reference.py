"""Read-only v2 audit; never runs the old generator's export section."""
import hashlib, json, sys, zipfile
from pathlib import Path
sys.path.insert(0, '/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as App
import Mesh
ROOT=Path(__file__).resolve().parent
OLD=ROOT.parent/'v2'
def bounds(b): return [b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax]
def audit():
    doc=App.openDocument(str(OLD/'garage-bookshelf-v2-assembly.FCStd'))
    records=[]
    for obj in doc.Objects:
        if obj.TypeId!='Mesh::Feature': continue
        source=Mesh.Mesh(str(OLD/'stl'/f'{obj.Name}.stl'))
        m=obj.Mesh
        components=m.getSeparateComponents()
        records.append(dict(name=obj.Name,label=obj.Label,group=[p.Label for p in obj.InList],bounds_global=bounds(m.BoundBox),bounds_source=bounds(source.BoundBox),placement=list(obj.Placement.Base)+list(obj.Placement.Rotation.Q),components=len(components),closed=all(c.isSolid() for c in components),volume_mm3=m.Volume,area_mm2=m.Area,facets=m.CountFacets,stl_facets=source.CountFacets))
    App.closeDocument(doc.Name)
    narrow_doc=App.openDocument(str(OLD/'garage-bookshelf-v2-narrow-visual.FCStd'))
    narrow_records=[dict(name=o.Name,label=o.Label,bounds_global=bounds(o.Mesh.BoundBox),placement=list(o.Placement.Base)+list(o.Placement.Rotation.Q),facets=o.Mesh.CountFacets,components=len(o.Mesh.getSeparateComponents())) for o in narrow_doc.Objects if o.TypeId=='Mesh::Feature']
    App.closeDocument(narrow_doc.Name)
    files=[]
    for p in sorted(OLD.rglob('*')):
        if p.is_file(): files.append(dict(path=str(p.relative_to(OLD)),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    packages=[]
    for p in sorted((OLD/'print/projects').glob('*.3mf')):
        with zipfile.ZipFile(p) as z:
            s=json.loads(z.read('Metadata/project_settings.config'))
            packages.append(dict(file=p.name,settings={k:s.get(k) for k in ['printer_model','printable_area','printable_height','wall_loops','sparse_infill_density','brim_width','layer_height','nozzle_diameter','filament_type']}))
    result=dict(freecad_version=App.Version(),assembly_objects=records,auxiliary_view_objects=narrow_records,assembly_count=len(records),physical_solids=sum(r['components'] for r in records),all_files=files,print_packages=packages)
    (ROOT/'reference/v2-inventory.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({k:result[k] for k in ['assembly_count','physical_solids']},indent=2))
    print(json.dumps(records,ensure_ascii=False,indent=2))
if __name__=='__main__': audit()
