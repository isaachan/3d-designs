"""Independent, read-only review of 098e652; writes only this review directory.
Run with the FreeCAD bundled Python. Production artifacts are not regenerated.
"""
import sys, json, itertools, zipfile, hashlib, xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
sys.path.insert(0, '/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as App
import Mesh, Part
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
SRC=ROOT/'bambu-print'
def tris(mesh): return np.array([[list(v) for v in f.Points] for f in mesh.Facets])
def canon(t): return sorted(tuple(sorted(tuple(np.round(v,4)) for v in tri)) for tri in t)
def bounds(t):
    p=t.reshape(-1,3)
    return np.round([p.min(0),p.max(0)],5).tolist()
def solid(t,name):
    converted=[]
    # The new columns contain coincident primitive end caps. FreeCAD's generic
    # component split creates open fragments and is unsafe for solid conversion.
    # Reconstruct the seven known 80-facet generating primitives for checking
    # intended geometry; package-and-topology.json separately records the defect.
    if name.startswith('07_'):
        assert len(t)==560
        components=[Mesh.Mesh(t[i:i+80].tolist()) for i in range(0,len(t),80)]
    else:
        components=Mesh.Mesh(t.tolist()).getSeparateComponents()
    for m in components:
        sh=Part.Shape(); sh.makeShapeFromMesh(m.Topology,.00001)
        for shell in sh.Shells:
            s=Part.makeSolid(shell)
            if s.Volume<0:s.reverse()
            assert s.isValid(), name
            converted.append(s)
    fused=converted[0]
    for s in converted[1:]:fused=fused.fuse(s)
    return fused

doc=App.openDocument(str(SRC/'garage-bookshelf-v4-装配检查.FCStd'))
world={}; local={}; records=[]
for o in doc.Objects:
    if o.TypeId!='Mesh::Feature':continue
    name=o.Name.lstrip('_'); m=o.Mesh.copy();m.Placement=App.Placement()
    t=tris(m); local[name]=t
    w=np.array([[list(o.Placement.multVec(App.Vector(*v))) for v in tri] for tri in t]);world[name]=w
    records.append(dict(name=name,facets=len(t),matches_stl=canon(t)==canon(tris(Mesh.Mesh(str(SRC/'stl'/f'{name}.stl')))),local_bounds=bounds(t),world_bounds=bounds(w)))
App.closeDocument(doc.Name)
solids={n:solid(t,n) for n,t in world.items() if not n.startswith(('12_','13_'))}
clashes=[]
for a,b in itertools.combinations(solids,2):
    ba,bb=np.array(bounds(world[a])),np.array(bounds(world[b]))
    if np.min(np.minimum(ba[1],bb[1])-np.maximum(ba[0],bb[0]))<.0001:continue
    v=solids[a].common(solids[b]).Volume
    if v>.001:clashes.append(dict(a=a,b=b,volume_mm3=v))

pairs=[
('05_right_panel_vertical_join_plate','05_right_panel_lower'),
('05_right_panel_vertical_join_plate','05_right_panel_upper'),
('04_divider_vertical_join_plate','04_divider_lower'),
('04_divider_vertical_join_plate','04_divider_upper'),
('09_billboard_join_plate_1','09_billboard_1'),
('09_billboard_join_plate_1','09_billboard_2'),
('09_billboard_join_plate_2','09_billboard_2'),
('09_billboard_join_plate_2','09_billboard_3'),
('10_billboard_post_1','02_back_r2_c2'),
('10_billboard_post_1','09_billboard_1'),
('06_garage_deck_1_left','02_back_r1_c1'),
('06_garage_deck_1_left','07_yellow_column_1'),
('06_garage_deck_1_left','07_yellow_column_3'),
('11_book_depot_sign','05_right_panel_lower')]
contacts=[dict(a=a,b=b,distance_mm=round(solids[a].distToShape(solids[b])[0],6)) for a,b in pairs]

# Render current text directly from STL coordinates, and measured contact gaps.
fig,axs=plt.subplots(1,2,figsize=(13,7))
for ax,n in zip(axs,['12_billboard_text_lovely_car_ive_driven','13_sign_text_book_depot']):
    t=local[n]; bb=np.array(bounds(t))
    ax.add_collection(PolyCollection(t[:,:,:2],facecolors='white',edgecolors='none'))
    ax.set(xlim=(bb[0,0]-5,bb[1,0]+5),ylim=(bb[0,1]-5,bb[1,1]+5),title=n[:2]+' — current STL, local XY')
    ax.set_facecolor('#263341');ax.set_aspect('equal')
fig.tight_layout();fig.savefig(OUT/'current-text.png',dpi=160);plt.close(fig)

ns={'c':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02','p':'http://schemas.microsoft.com/3dmanufacturing/production/2015/06'}
def tf(s):
    v=np.array([float(x) for x in s.split()]) if s else np.array([1,0,0,0,1,0,0,0,1,0,0,0])
    m=np.eye(4);m[:3,:3]=v[:9].reshape(3,3).T;m[:3,3]=v[9:];return m
projects=[]
for p in sorted(SRC.glob('*.3mf')):
    z=zipfile.ZipFile(p);root=ET.fromstring(z.read('3D/3dmodel.model'))
    cfg=ET.fromstring(z.read('Metadata/model_settings.config'))
    settings=json.loads(z.read('Metadata/project_settings.config'))
    names={o.get('id'):next(m.get('value') for m in o.findall('metadata') if m.get('key')=='name') for o in cfg.findall('object')}
    res={o.get('id'):o for o in root.findall('c:resources/c:object',ns)}
    items=[]
    for item in root.findall('c:build/c:item',ns):
        oid=item.get('objectid');parts=[]
        for c in res[oid].findall('c:components/c:component',ns):
            sub=ET.fromstring(z.read(c.get('{'+ns['p']+'}path').lstrip('/')))
            obj=next(o for o in sub.findall('c:resources/c:object',ns) if o.get('id')==c.get('objectid'))
            v=np.array([[float(x.get(a)) for a in ('x','y','z')] for x in obj.findall('c:mesh/c:vertices/c:vertex',ns)])
            f=np.array([[int(x.get(a)) for a in ('v1','v2','v3')] for x in obj.findall('c:mesh/c:triangles/c:triangle',ns)])
            loc=(np.c_[v,np.ones(len(v))]@tf(c.get('transform')).T)[:,:3]
            n=names[oid].removesuffix('.stl')
            parts.append(dict(local_bounds=bounds(loc[f]),facets=len(f),source_exists=n in local,matches_current_stl=n in local and canon(loc[f])==canon(local[n])))
        items.append(dict(name=names[oid],parts=parts))
    projects.append(dict(file=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),plates=len(cfg.findall('plate')),items=items,settings={k:settings.get(k) for k in ['wall_loops','sparse_infill_density','brim_type','brim_width','enable_support','support_type']}))

out=dict(solid_check_note='Column solids reconstructed from 7 known closed generating primitives; raw column mesh is non-manifold. See package-and-topology.json.',stl_count=len(list((SRC/'stl').glob('*.stl'))),mesh_count=len(records),meshes=records,clashes=clashes,contacts=contacts,projects=projects)
(OUT/'review-measurements.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps(dict(mesh_count=len(records),stl_matches=sum(r['matches_stl'] for r in records),clashes=clashes,contacts=contacts,projects=[dict(file=p['file'],matches=sum(all(part['matches_current_stl'] for part in item['parts']) for item in p['items']),count=len(p['items']),settings=p['settings']) for p in projects]),ensure_ascii=False,indent=2))
