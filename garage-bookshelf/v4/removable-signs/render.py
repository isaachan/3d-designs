"""Software-render actual CAD faces; avoids the macOS Qt accessibility crash."""
import sys,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent));sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as A,MeshPart,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from assembly import global_shape
D=A.openDocument(str(ROOT/'removable-signs-assembly.FCStd'))

def render(exploded=False):
 fig=plt.figure(figsize=(15,10),facecolor='white');ax=fig.add_subplot(111,projection='3d');bounds=[];all_triangles=[];all_colors=[]
 for b in D.Objects:
  if b.TypeId!='PartDesign::Body':continue
  name=b.SourcePart
  if exploded and not (name.startswith('billboard') or name.startswith('top_carrier') or name.startswith('side_') or name.startswith('lock_pin')):continue
  shape=global_shape(b);color=(.12,.14,.16) if name.startswith(('billboard','top_carrier')) else (.12,.39,.85) if name.startswith('side_') else (.98,.72,.1) if name.startswith(('column','lock_pin')) else (.56,.60,.65)
  if name.startswith('billboard_text'):color=(.95,.95,.95)
  delta=np.zeros(3)
  if exploded:
   if name.startswith(('top_carrier','billboard_text')):delta[0]=55
   if name=='side_cartridge':delta[2]=60
   if name.startswith('lock_pin'):delta[1]=-15
  triangles=[];colors=[]
  # Per-face tessellation preserves the engraved white paint preview.
  for f in shape.Faces:
   facecolor=color
   if name=='side_cartridge' and abs(f.CenterOfMass.y+1.4)<1e-5 and f.normalAt(0,0).y<-.99:facecolor=(.95,.95,.95)
   vertices,indices=f.tessellate(.18)
   if not indices:continue
   v=np.array([[p.x,p.y,p.z] for p in vertices])+delta;t=v[np.array(indices)]
   n=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);n/=np.maximum(np.linalg.norm(n,axis=1)[:,None],1e-12)
   light=np.array([-.4,-.65,.75]);light/=np.linalg.norm(light)
   shade=.60+.4*np.abs(n@light)
   triangles.extend(t);colors.extend(np.array(facecolor)[None,:]*shade[:,None])
  all_triangles.extend(triangles);all_colors.extend(colors)
  bounds.extend(np.array(triangles).reshape(-1,3))
 # Orthographic software Z buffer: large receiver faces must not occlude nearer lettering.
 from PIL import Image
 t=np.array(all_triangles);color=np.array(all_colors)
 toward=np.array([1.,-1.8,1.05]);toward/=np.linalg.norm(toward)
 right=np.cross([0.,0.,1.],toward);right/=np.linalg.norm(right);up=np.cross(toward,right)
 basis=np.stack([right,up,toward],axis=1);projected=t@basis
 lo=projected.reshape(-1,3).min(axis=0);hi=projected.reshape(-1,3).max(axis=0)
 w,h=1800,1200;scale=min((w-160)/(hi[0]-lo[0]),(h-120)/(hi[1]-lo[1]))
 projected[:,:,0]=(projected[:,:,0]-(lo[0]+hi[0])/2)*scale+w/2
 projected[:,:,1]=h/2-(projected[:,:,1]-(lo[1]+hi[1])/2)*scale
 canvas=np.full((h,w,3),255,dtype=np.uint8);depth=np.full((h,w),-np.inf)
 for tri,rgb in zip(projected,color):
  xmin=max(0,int(np.floor(tri[:,0].min())));xmax=min(w-1,int(np.ceil(tri[:,0].max())))
  ymin=max(0,int(np.floor(tri[:,1].min())));ymax=min(h-1,int(np.ceil(tri[:,1].max())))
  if xmax<xmin or ymax<ymin:continue
  x,y=np.meshgrid(np.arange(xmin,xmax+1)+.5,np.arange(ymin,ymax+1)+.5)
  a,b,c=tri;den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
  if abs(den)<1e-10:continue
  u=((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/den
  v=((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/den;zz=u*a[2]+v*b[2]+(1-u-v)*c[2]
  z=depth[ymin:ymax+1,xmin:xmax+1];mask=(u>=-1e-8)&(v>=-1e-8)&(u+v<=1+1e-8)&(zz>z)
  z[mask]=zz[mask];canvas[ymin:ymax+1,xmin:xmax+1][mask]=(rgb*255).astype(np.uint8)
 Image.fromarray(canvas).save(ROOT/'reports'/('signs-exploded.png' if exploded else 'assembly-preview.png'))
 plt.close(fig)
render();render(True)
(ROOT/'reports/render-validation.json').write_text(json.dumps(dict(status='passed',source='actual native CAD faces tessellated with OpenCascade; software rendered',cad_sha256=hashlib.sha256((ROOT/'removable-signs-assembly.FCStd').read_bytes()).hexdigest()),indent=2))
print('PASS actual CAD previews rendered')

import runpy
runpy.run_path(str(ROOT/'draw_interface.py'))
