"""Read-only verification of the column topology fix in 2dece02.
Uses raw current meshes, without the previous 80-facet reconstruction workaround.
Run with /Applications/FreeCAD.app/Contents/Resources/bin/python.
"""
from pathlib import Path
import sys,json,subprocess,collections,itertools,zipfile,xml.etree.ElementTree as E
import numpy as np
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as A
import Mesh,Part
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1];SRC=ROOT/'bambu-print'
def triangles(m):return np.array([[list(v) for v in f.Points] for f in m.Facets])
def canon(t):return sorted(tuple(sorted(tuple(np.round(v,4)) for v in tri)) for tri in t)
def solid(t):
    shape=Part.Shape();shape.makeShapeFromMesh(Mesh.Mesh(t.tolist()).Topology,.00001)
    assert len(shape.Shells)==1
    obj=Part.makeSolid(shape.Shells[0]);assert obj.isValid()
    if obj.Volume<0:obj.reverse()
    return obj
def topology(t):
    facets=collections.Counter(canon(t));edges=collections.Counter();directed=collections.Counter();points=set()
    for face in t:
        p=[tuple(np.round(v,5)) for v in face];points.update(p)
        for a,b in zip(p,p[1:]+p[:1]):edges[tuple(sorted((a,b)))]+=1;directed[(a,b)]+=1
    m=Mesh.Mesh(t.tolist());s=solid(t)
    return dict(facets=len(t),vertices=len(points),edges=len(edges),euler=len(points)-len(edges)+len(t),
        duplicate_faces=sum(n-1 for n in facets.values()),non_two_incident_edges=sum(n!=2 for n in edges.values()),
        inconsistent_oriented_edges=sum(directed[(a,b)]!=directed[(b,a)] for a,b in edges),
        is_solid=m.isSolid(),components=len(m.getSeparateComponents()),part_valid=s.isValid(),volume_mm3=s.Volume,
        bounds=np.round([t.reshape(-1,3).min(0),t.reshape(-1,3).max(0)],5).tolist())

doc=A.openDocument(str(SRC/'garage-bookshelf-v4-装配检查.FCStd'))
local={};world={};placements={};matches=[]
for o in doc.Objects:
    if o.TypeId!='Mesh::Feature':continue
    n=o.Name.lstrip('_');m=o.Mesh.copy();m.Placement=A.Placement();t=triangles(m)
    local[n]=t;world[n]=np.array([[list(o.Placement.multVec(A.Vector(*v))) for v in face] for face in t]);placements[n]=list(o.Placement.Matrix.A)
    matches.append(dict(name=n,match=canon(t)==canon(triangles(Mesh.Mesh(str(SRC/'stl'/f'{n}.stl'))))))
A.closeDocument(doc.Name)
columns={n:topology(triangles(Mesh.Mesh(str(SRC/'stl'/f'{n}.stl')))) for n in local if n.startswith('07_')}
shapes={n:solid(t) for n,t in world.items() if not n.startswith(('12_','13_'))}
clashes=[]
for a,b in itertools.combinations(shapes,2):
    if not shapes[a].BoundBox.intersect(shapes[b].BoundBox):continue
    volume=shapes[a].common(shapes[b]).Volume
    if volume>.001:clashes.append(dict(a=a,b=b,volume_mm3=volume))
contacts=[]
for level,z in enumerate((66,129,192),1):
    for col in range(1,5):
        n=f'07_yellow_column_{col}';d=f'06_garage_deck_{level}_'+('left' if col in (1,3) else 'right')
        sf=[f for f in shapes[n].Faces if abs(f.BoundBox.ZMin-z)<1e-5 and abs(f.BoundBox.ZMax-z)<1e-5]
        df=[f for f in shapes[d].Faces if abs(f.BoundBox.ZMin-z)<1e-5 and abs(f.BoundBox.ZMax-z)<1e-5]
        contacts.append(dict(column=n,deck=d,distance_mm=shapes[n].distToShape(shapes[d])[0],area_mm2=sum(a.common(b).Area for a in sf for b in df)))

# Compare current closed boundary with the union of old generating primitives,
# sourced from the immutable previous commit, not from regenerated files.
previous=json.loads(subprocess.check_output(['git','show','098e652:garage-bookshelf/audit/freecad-meshes.json'],cwd=ROOT.parent))
previous={o['name']:o for o in previous}
n='07_yellow_column_1';old=np.array(previous[n]['triangles']);assert len(old)==560
parts=[solid(old[i:i+80]) for i in range(0,560,80)]
fused=parts[0]
for s in parts[1:]:fused=fused.fuse(s)
comparison=dict(old_union_valid=fused.isValid(),old_union_volume=fused.Volume,new_volume=shapes[n].Volume,
    old_minus_new_mm3=fused.cut(shapes[n]).Volume,new_minus_old_mm3=shapes[n].cut(fused).Volume,
    all_four_local_meshes_identical=all(canon(local[c])==canon(local[n]) for c in columns),
    all_four_placements_unchanged=all(np.allclose(previous[c]['placement'],placements[c],atol=1e-8) for c in columns))

ns={'c':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02','p':'http://schemas.microsoft.com/3dmanufacturing/production/2015/06'}
def tf(s):
    v=np.array(list(map(float,s.split()))) if s else np.array([1,0,0,0,1,0,0,0,1,0,0,0])
    m=np.eye(4);m[:3,:3]=v[:9].reshape(3,3).T;m[:3,3]=v[9:];return m
z=zipfile.ZipFile(SRC/'02-黄色立柱-x2d-pla.3mf');root=E.fromstring(z.read('3D/3dmodel.model'));cfg=E.fromstring(z.read('Metadata/model_settings.config'))
names={o.get('id'):next(m.get('value') for m in o.findall('metadata') if m.get('key')=='name').removesuffix('.stl') for o in cfg.findall('object')}
three_mf=[]
for obj in root.findall('c:resources/c:object',ns):
    for c in obj.findall('c:components/c:component',ns):
        sub=E.fromstring(z.read(c.get('{'+ns['p']+'}path').lstrip('/')))
        mesh=next(o for o in sub.findall('c:resources/c:object',ns) if o.get('id')==c.get('objectid'))
        vertices=np.array([[float(v.get(a)) for a in ('x','y','z')] for v in mesh.findall('c:mesh/c:vertices/c:vertex',ns)])
        faces=np.array([[int(t.get(a)) for a in ('v1','v2','v3')] for t in mesh.findall('c:mesh/c:triangles/c:triangle',ns)])
        vertices=(np.c_[vertices,np.ones(len(vertices))]@tf(c.get('transform')).T)[:,:3];n=names[obj.get('id')]
        three_mf.append(dict(name=n,matches_current_stl=canon(vertices[faces])==canon(local[n]),is_solid=Mesh.Mesh(vertices[faces].tolist()).isSolid()))
result=dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT.parent,text=True).strip(),
    column_topology=columns,fcstd_matches=matches,assembly_clashes=clashes,support_contacts=contacts,comparison_with_old_union=comparison,yellow_3mf=three_mf)
(OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(dict(column_topology=columns,fcstd_matches=sum(r['match'] for r in matches),assembly_clashes=clashes,support_contacts=contacts,comparison=comparison,yellow_3mf=three_mf),ensure_ascii=False,indent=2))
