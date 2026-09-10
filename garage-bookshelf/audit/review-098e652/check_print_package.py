"""Read actual saved build transforms, plate membership, and column topology."""
import json, zipfile, collections, xml.etree.ElementTree as E, sys
from pathlib import Path
import numpy as np
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as A
import Mesh, Part
OUT=Path(__file__).resolve().parent
SRC=OUT.parents[1]/'bambu-print'
ns={'c':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02','p':'http://schemas.microsoft.com/3dmanufacturing/production/2015/06'}
def tf(s):
    v=np.array(list(map(float,s.split()))) if s else np.array([1,0,0,0,1,0,0,0,1,0,0,0])
    m=np.eye(4);m[:3,:3]=v[:9].reshape(3,3).T;m[:3,3]=v[9:];return m
projects=[]
for p in sorted(SRC.glob('*.3mf')):
    z=zipfile.ZipFile(p);root=E.fromstring(z.read('3D/3dmodel.model'));cfg=E.fromstring(z.read('Metadata/model_settings.config'))
    settings=json.loads(z.read('Metadata/project_settings.config'))
    names={o.get('id'):next(m.get('value') for m in o.findall('metadata') if m.get('key')=='name') for o in cfg.findall('object')}
    plates=[]; membership={}
    for i,plate in enumerate(cfg.findall('plate'),1):
        ids=[next(m.get('value') for m in inst.findall('metadata') if m.get('key')=='object_id') for inst in plate.findall('model_instance')]
        plates.append(dict(index=i,objects=[names[n] for n in ids]))
        for n in ids: membership[n]=i
    objects={o.get('id'):o for o in root.findall('c:resources/c:object',ns)}
    items=[]
    for item in root.findall('c:build/c:item',ns):
        allpts=[]
        for c in objects[item.get('objectid')].findall('c:components/c:component',ns):
            sub=E.fromstring(z.read(c.get('{'+ns['p']+'}path').lstrip('/')))
            obj=next(o for o in sub.findall('c:resources/c:object',ns) if o.get('id')==c.get('objectid'))
            pts=np.array([[float(v.get(a)) for a in ('x','y','z')] for v in obj.findall('c:mesh/c:vertices/c:vertex',ns)])
            m=tf(item.get('transform'))@tf(c.get('transform'))
            allpts.extend((np.c_[pts,np.ones(len(pts))]@m.T)[:,:3])
        pts=np.array(allpts)
        items.append(dict(name=names[item.get('objectid')],plate=membership.get(item.get('objectid')),bounds=np.round([pts.min(0),pts.max(0)],5).tolist(),size=np.round(pts.max(0)-pts.min(0),5).tolist()))
    projects.append(dict(file=p.name,settings={k:settings.get(k) for k in ['printer_model','printer_settings_id','printable_area','printable_height','wall_loops','sparse_infill_density','brim_width']},plates=plates,items=items,unassigned=[i['name'] for i in items if i['plate'] is None]))

mesh=Mesh.Mesh(str(SRC/'stl/07_yellow_column_1.stl'))
t=np.array([[list(v) for v in f.Points] for f in mesh.Facets])
def canonical(tri):return tuple(sorted(tuple(np.round(v,5)) for v in tri))
counts=collections.Counter(canonical(tri) for tri in t)
components=mesh.getSeparateComponents()
column=dict(facets=len(t),is_solid=mesh.isSolid(),component_counts=dict(collections.Counter(x.CountFacets for x in components)),duplicate_triangle_pairs=sum(c==2 for c in counts.values()))
# Reconstruct each closed generating primitive separately to inspect intended
# support geometry, without modifying the invalid source STL. Each primitive
# uses 80 triangles: main cylinder, then three frustum/cylinder pairs.
parts=[]
for i in range(0,len(t),80):
    m=Mesh.Mesh(t[i:i+80].tolist());s=Part.Shape();s.makeShapeFromMesh(m.Topology,.00001)
    assert len(s.Shells)==1
    solid=Part.makeSolid(s.Shells[0]);assert solid.isValid()
    if solid.Volume<0:solid.reverse()
    parts.append(solid)
fused=parts[0]
for s in parts[1:]:fused=fused.fuse(s)
column['primitive_union_valid']=fused.isValid()
column['primitive_union_volume']=fused.Volume
fused.translate(A.Vector(0,0,8))
deckmesh=Mesh.Mesh(str(SRC/'stl/06_garage_deck_1_left.stl'))
shape=Part.Shape();shape.makeShapeFromMesh(deckmesh.Topology,.00001)
deck=Part.makeSolid(shape.Shells[0]);deck.translate(A.Vector(0,0,66))
column['intended_deck_distance']=fused.distToShape(deck)[0]
column['intended_deck_collision_volume']=fused.common(deck).Volume
column['intended_contact_area']=sum(a.common(b).Area for a in fused.Faces for b in deck.Faces if abs(a.BoundBox.ZMin-66)<1e-5 and abs(a.BoundBox.ZMax-66)<1e-5 and abs(b.BoundBox.ZMin-66)<1e-5 and abs(b.BoundBox.ZMax-66)<1e-5)
(OUT/'package-and-topology.json').write_text(json.dumps(dict(projects=projects,column=column),ensure_ascii=False,indent=2))
print(json.dumps(dict(projects=[dict(file=p['file'],settings=p['settings'],plate_counts=[len(q['objects']) for q in p['plates']],unassigned=p['unassigned']) for p in projects],column=column),ensure_ascii=False,indent=2))
