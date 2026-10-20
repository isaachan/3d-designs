"""The raster design's 2D outline becomes editable Sketch geometry, never a final static Shape."""
import json
from pathlib import Path
import FreeCAD as App,Part
from assembly import part
from geometry.sketches import loops,rectangle
from geometry.features import pad
ROOT=Path(__file__).resolve().parents[1]

def box(body,width,depth,height):
    return pad(body,'Pad_Base',rectangle(body,'Sketch_Base',width,depth),height)

def coordinate(v):
    # Original mask bounds are integers +/- half the source 0.1mm overlap.
    integer=round(v);sign=1 if v>integer+1e-7 else -1 if v<integer-1e-7 else 0
    return f'{integer}*TextPixel'+(' + TextOverlap/2' if sign==1 else ' - TextOverlap/2' if sign==-1 else '')

def profiles(name):
    runs=json.loads((ROOT/'reference/text-masks.json').read_text())[name]
    faces=[]
    for x,y,n in runs:
        # Exact planar union is only an outline calculation on source design data.
        p=[App.Vector(x-.05,y-.05,0),App.Vector(x+n+.05,y-.05,0),App.Vector(x+n+.05,y+1.05,0),App.Vector(x-.05,y+1.05,0)]
        faces.append(Part.Face(Part.makePolygon(p+[p[0]])).extrude(App.Vector(0,0,1)))
    union=faces[0].multiFuse(faces[1:]).removeSplitter()
    result=[]
    top_faces=[f for f in union.Faces if abs(f.CenterOfMass.z-1)<1e-7 and abs(f.normalAt(0,0).z)>0.99]
    for face in sorted(top_faces,key=lambda f:(f.CenterOfMass.x,f.CenterOfMass.y)):
        polygons=[]
        for wire in face.Wires:
            points=[(coordinate(v.Point.x),coordinate(v.Point.y)) for v in wire.OrderedVertexes]
            polygons.append(points)
        result.append(polygons)
    if len(result)!=10:raise RuntimeError(f'{name}: source text changed: {len(result)} islands')
    return result

def text(doc,parent,name,label,z):
    container,_=part(doc,parent,name,label,('TextOriginX','OverallDepth','TextLovelyZ' if z==332 else 'TextDrivenZ'),body=False,color='text')
    result=profiles(name)
    for i,polygons in enumerate(result,1):
        b=doc.addObject('PartDesign::Body',name+f'_island_{i:02}');b.Label=f'{label} 字形岛 {i:02}';container.addObject(b)
        b.addProperty('App::PropertyString','SourcePart','Design reference');b.SourcePart=name
        if b.ViewObject is not None:b.ViewObject.ShapeColor=(.95,.95,.95)
        pad(b,'Pad_Text',loops(b,'Sketch_TextOutline',polygons,orientation='XZ'),'TextThickness')
    return container
