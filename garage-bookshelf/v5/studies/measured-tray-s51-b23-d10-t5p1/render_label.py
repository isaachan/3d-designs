"""Read-only native CAD views with technical outlines on the raised lettering."""
import hashlib
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[1]/'src'))
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as App
import Part
import numpy as np
from PIL import Image,ImageDraw
from garage_bookshelf.rendering.software import render


def tessellate(shape):
    points=[];paint=[]
    light=np.array([-.45,-.65,.85]);light/=np.linalg.norm(light)
    for face in shape.Faces:
        vertices,indices=face.tessellate(.05)
        if not indices:continue
        xyz=np.array([[v.x,v.y,v.z] for v in vertices])
        tri=xyz[np.array(indices)]
        normals=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])
        normals/=np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-12)
        shade=.55+.45*np.abs(normals@light)
        points.extend(tri);paint.extend(np.array([.38,.43,.49])[None,:]*shade[:,None])
    return np.array(points),np.array(paint)


def outlined_view(shape,letters,path,toward,width,height):
    points,paint=tessellate(shape)
    render(points,paint,path,toward,width=width,height=height)
    toward=np.array(toward,dtype=float);toward/=np.linalg.norm(toward)
    right=np.cross([0.,0.,1.],toward);right/=np.linalg.norm(right)
    up=np.cross(toward,right)
    matrix=np.stack([right,up,toward],axis=1)
    projected=points@matrix
    lo=projected.reshape(-1,3).min(axis=0);hi=projected.reshape(-1,3).max(axis=0)
    scale=min((width-120)/(hi[0]-lo[0]),(height-100)/(hi[1]-lo[1]))
    image=Image.open(path).convert('RGB');draw=ImageDraw.Draw(image)
    # Exact top-perimeter edges only: dark strokes are a CAD display aid,
    # not additional material or a second print colour.
    for edge in letters.Edges:
        if abs(edge.BoundBox.ZMin-letters.BoundBox.ZMax)>1e-6:continue
        vertices=edge.discretize(Deflection=.01)
        xy=np.array([[v.x,v.y,v.z] for v in vertices])@matrix
        xy[:,0]=(xy[:,0]-(lo[0]+hi[0])/2)*scale+width/2
        xy[:,1]=height/2-(xy[:,1]-(lo[1]+hi[1])/2)*scale
        draw.line([tuple(p[:2]) for p in xy],fill=(19,25,31),width=2)
    image.save(path)


def main():
    files=[ROOT/'parking-tray-s51-b23-d10-t5p1.FCStd',ROOT/'parking-tray-s51-b23-d10-t5p1.3mf']
    hashes=[hashlib.sha256(p.read_bytes()).hexdigest() for p in files]
    doc=App.openDocument(str(files[0]))
    shape=doc.measured_tray_Body.Shape
    letters=shape.cut(doc.Pocket_Rear_2_TireArc.Shape)
    assert len(letters.Solids)==8
    assert abs(letters.BoundBox.ZLength-doc.ModelLabel.RaisedHeight.Value)<1e-6
    outlined_view(shape,letters,ROOT/'tray-preview.png',[-1.1,-1.65,2.4],1400,1100)
    front=shape.common(Part.makeBox(40,13,3.6,App.Vector(-20,-43,0)))
    outlined_view(front,letters,ROOT/'tray-label-detail.png',[0,-1.8,3.4],1500,640)
    App.closeDocument(doc.Name)
    assert hashes==[hashlib.sha256(p.read_bytes()).hexdigest() for p in files]
    print('Rendered exact native lettering with technical edge outlines; CAD and 3MF unchanged.')


if __name__=='__main__':main()
