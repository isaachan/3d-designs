"""Measure actual saved mesh geometry and render audit views; no source edits.
Run with FreeCAD's bundled Python (numpy, matplotlib, Part available).
"""
import sys, json, itertools, zipfile, xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
sys.path.insert(0, '/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as App
import Part, Mesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib.colors import LightSource

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'audit'
data = json.loads((OUT/'freecad-meshes.json').read_text())
objects = {}
for obj in data:
    tri = np.array(obj.pop('triangles'))
    pts = tri.reshape(-1,3)
    obj['bounds'] = np.round([pts.min(0), pts.max(0)],5).tolist()
    obj['size'] = np.round(pts.max(0)-pts.min(0),5).tolist()
    objects[obj['name']] = (obj,tri)

# Boolean intersection tests on individually closed shells. Text has many
# touching pixel-run boxes and is measured/rendered but omitted from booleans.
solids = {}
for name,(obj,tri) in objects.items():
    if name.startswith(('12_','13_')): continue
    mesh = Mesh.Mesh(tri.tolist())
    shells = mesh.getSeparateComponents()
    converted = []
    for shell in shells:
        shape = Part.Shape()
        shape.makeShapeFromMesh(shell.Topology, 0.00001)
        for sh in shape.Shells:
            solid = Part.makeSolid(sh)
            if solid.Volume < 0: solid.reverse()
            converted.append(solid)
    obj['shells'] = len(shells)
    obj['valid_solids'] = all(s.isValid() for s in converted)
    fused = converted[0]
    for s in converted[1:]: fused = fused.fuse(s)
    solids[name] = fused

clashes = []
for a,b in itertools.combinations(solids,2):
    ba,bb = np.array(objects[a][0]['bounds']),np.array(objects[b][0]['bounds'])
    overlap = np.minimum(ba[1],bb[1])-np.maximum(ba[0],bb[0])
    if np.min(overlap) < 0.0001: continue
    common = solids[a].common(solids[b])
    if common.Volume > 0.001:
        clashes.append(dict(a=a,b=b,volume_mm3=round(common.Volume,3)))

def color(n):
    if n.startswith('07_'): return '#efb51f'
    if n.startswith(('09_','10_')): return '#262b31'
    if n.startswith('11_'): return '#1263d7'
    if n.startswith(('12_','13_')): return '#fdfdfd'
    return '#929da8'

fig = plt.figure(figsize=(16,9))
ax = fig.add_subplot(projection='3d')
for n,(obj,tri) in objects.items():
    ax.add_collection3d(Poly3DCollection(tri, facecolors=color(n), edgecolors=None, linewidth=0,
                                        shade=True, lightsource=LightSource(azdeg=315,altdeg=45)))
ax.set(xlim=(0,980),ylim=(-150,230),zlim=(0,510),xlabel='X / mm',ylabel='Y / mm',zlabel='Z / mm')
ax.set_box_aspect((980,380,510)); ax.view_init(elev=17,azim=-65)
ax.set_title('Actual saved FreeCAD assembly — all 61 STL meshes',fontsize=17)
fig.tight_layout(); fig.savefig(OUT/'actual-assembly.png',dpi=160); plt.close(fig)

fig,axs=plt.subplots(1,2,figsize=(16,7),gridspec_kw={'width_ratios':[3,2]})
from matplotlib.collections import PolyCollection
front_triangles=[]
for n,(obj,tri) in objects.items():
    front_triangles.extend((t[:,1].mean(),t[:,[0,2]],color(n)) for t in tri)
front_triangles.sort(key=lambda t:t[0],reverse=True)
axs[0].add_collection(PolyCollection([t[1] for t in front_triangles],facecolors=[t[2] for t in front_triangles],edgecolors='#74808a',linewidths=.1))
axs[0].set(xlim=(-20,990),ylim=(-10,520),xlabel='X / mm',ylabel='Z / mm',title='Front projection (looking toward +Y)')
axs[0].set_aspect('equal')
for n,(obj,tri) in objects.items():
    if n.startswith(('02_','06_','07_')):
        axs[1].add_collection(PolyCollection(tri[:,:,[1,2]],facecolors=color(n),edgecolors='#596570',linewidths=.3))
axs[1].set(xlim=(-10,240),ylim=(0,320),xlabel='Y / mm',ylabel='Z / mm',title='Garage side projection: parking depth 215 mm')
axs[1].set_aspect('equal')
axs[1].annotate('',xy=(150,105),xytext=(215,105),arrowprops=dict(arrowstyle='<->',color='#cf3030',lw=2))
axs[1].text(100,110,'215 mm',color='#444444')
fig.tight_layout(); fig.savefig(OUT/'orthographic-check.png',dpi=150); plt.close(fig)

fig,axs=plt.subplots(1,2,figsize=(13,7))
for ax,name in zip(axs,['12_billboard_text_lovely_car_ive_driven','13_sign_text_book_depot']):
    mesh=Mesh.Mesh(str(ROOT/'bambu-print/stl'/f'{name}.stl'))
    tris=np.array([[list(v) for v in f.Points] for f in mesh.Facets])
    ax.add_collection(PolyCollection(tris[:,:,:2],facecolors='#ffffff',edgecolors='none'))
    pts=tris.reshape(-1,3)
    ax.set(xlim=(pts[:,0].min()-5,pts[:,0].max()+5),ylim=(pts[:,1].min()-5,pts[:,1].max()+5))
    ax.set_facecolor('#263341'); ax.set_aspect('equal'); ax.set_title(name[:2]+' — actual STL, local XY')
fig.tight_layout(); fig.savefig(OUT/'text-meshes.png',dpi=170); plt.close(fig)

fig,axs=plt.subplots(1,3,figsize=(14,6))
for ax,left,right,title in zip(axs,['01_base_01','01_base_02','01_base_03'],['01_base_02','01_base_03','01_base_04'],['Seam 1: upper half overlaps','Seam 2: upper tongue missing','Seam 3: upper half overlaps']):
    seam=objects[right][0]['bounds'][0][0]
    for name,c in [(left,'#69a4c6'),(right,'#ecbb68')]:
        for wire in solids[name].slice(App.Vector(0,0,1),6):
            pts=[(v.x,v.y) for v in wire.discretize(Deflection=0.01)]
            ax.fill(*np.array(pts).T,color=c,alpha=.65,edgecolor='#33414e')
    common=solids[left].common(solids[right])
    if common.Volume>0.01:
        for wire in common.slice(App.Vector(0,0,1),6):
            pts=[(v.x,v.y) for v in wire.discretize(Deflection=0.01)]
            ax.fill(*np.array(pts).T,color='#df3737')
    ax.set(xlim=(seam-15,seam+25),ylim=(0,100),xlabel='X / mm',ylabel='Y / mm',title=title)
    ax.set_aspect('equal')
fig.suptitle('Revised base joint cross-sections at Z = 6 mm',fontsize=15)
fig.tight_layout(); fig.savefig(OUT/'base-joints.png',dpi=160); plt.close(fig)

ns={'c':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02','p':'http://schemas.microsoft.com/3dmanufacturing/production/2015/06'}
def transform(s):
    vals=np.array([float(x) for x in s.split()]) if s else np.array([1,0,0,0,1,0,0,0,1,0,0,0])
    m=np.eye(4); m[:3,:3]=vals[:9].reshape(3,3).T; m[:3,3]=vals[9:]; return m
projects=[]
for path in sorted((ROOT/'bambu-print').glob('*.3mf')):
    z=zipfile.ZipFile(path)
    model=ET.fromstring(z.read('3D/3dmodel.model'))
    settings=json.loads(z.read('Metadata/project_settings.config'))
    config=ET.fromstring(z.read('Metadata/model_settings.config'))
    names={o.get('id'):next((m.get('value') for m in o.findall('metadata') if m.get('key')=='name'),'') for o in config.findall('object')}
    res={o.get('id'):o for o in model.findall('c:resources/c:object',ns)}
    items=[]
    for item in model.findall('c:build/c:item',ns):
        oid=item.get('objectid'); pts=[]; local_bounds=[]; mesh_matches=[]
        for comp in res[oid].findall('c:components/c:component',ns):
            sub=ET.fromstring(z.read(comp.get('{'+ns['p']+'}path').lstrip('/')))
            subobj=next(o for o in sub.findall('c:resources/c:object',ns) if o.get('id')==comp.get('objectid'))
            vertices=np.array([[float(v.get(a)) for a in ('x','y','z')] for v in subobj.findall('c:mesh/c:vertices/c:vertex',ns)])
            faces=np.array([[int(t.get(a)) for a in ('v1','v2','v3')] for t in subobj.findall('c:mesh/c:triangles/c:triangle',ns)])
            mat=transform(comp.get('transform'))
            local=(np.c_[vertices,np.ones(len(vertices))]@mat.T)[:,:3]
            local_bounds.append(np.round([local.min(0),local.max(0)],4).tolist())
            source=Mesh.Mesh(str(ROOT/'bambu-print/stl'/names[oid]))
            source_tris=np.array([[list(v) for v in f.Points] for f in source.Facets])
            def canonical(t): return sorted(tuple(sorted(tuple(np.round(v,3)) for v in tri)) for tri in t)
            mesh_matches.append(canonical(local[faces])==canonical(source_tris))
            world=(np.c_[local,np.ones(len(local))]@transform(item.get('transform')).T)[:,:3]
            pts.extend(world)
        pts=np.array(pts)
        items.append(dict(name=names[oid],bounds=np.round([pts.min(0),pts.max(0)],4).tolist(),size=np.round(pts.max(0)-pts.min(0),4).tolist(),matches_stl=all(mesh_matches)))
    projects.append(dict(file=path.name,plates=len(config.findall('plate')),objects=len(items),settings={k:settings[k] for k in settings if any(s in k for s in ['printable','printer_model','wall_loops','sparse_infill','layer_height','brim_type','brim_width','support_enable'])},items=items))

(OUT/'measurements.json').write_text(json.dumps(dict(meshes=data,clashes=clashes,projects=projects),ensure_ascii=False,indent=2))
print('Clashes:',json.dumps(clashes,indent=2))
print('Projects:',json.dumps([{k:v for k,v in p.items() if k!='items'} for p in projects],ensure_ascii=False,indent=2))
