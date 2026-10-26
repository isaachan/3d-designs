"""The raster design's 2D outline becomes editable Sketch geometry, never a final static Shape."""
import json
from pathlib import Path
import FreeCAD as App,Part
from garage_bookshelf.assembly import part
from garage_bookshelf.geometry.sketches import loops,rectangle
from garage_bookshelf.geometry.features import pad,pocket,finish
from garage_bookshelf.parameters import expression,evaluate
from garage_bookshelf.paths import LETTERING

def box(body,width,depth,height):
    return pad(body,'Pad_Base',rectangle(body,'Sketch_Base',width,depth),height)

def coordinate(v):
    # Original mask bounds are integers +/- half the source 0.1mm overlap.
    integer=round(v);sign=1 if v>integer+1e-7 else -1 if v<integer-1e-7 else 0
    return f'{integer}*TextPixel'+(' + TextOverlap/2' if sign==1 else ' - TextOverlap/2' if sign==-1 else '')

def profiles(name):
    runs=json.loads((LETTERING/'text-masks.json').read_text())[name]
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
    container,_=part(doc,parent,name,label,('TextOriginX','BillboardY','TextLovelyZ' if z==332 else 'TextDrivenZ'),body=False,color='text')
    result=profiles(name)
    for i,polygons in enumerate(result,1):
        b=doc.addObject('PartDesign::Body',name+f'_island_{i:02}');b.Label=f'{label} 字形岛 {i:02}';container.addObject(b)
        b.addProperty('App::PropertyString','SourcePart','Design reference');b.SourcePart=name
        if b.ViewObject is not None:b.ViewObject.ShapeColor=(.95,.95,.95)
        pad(b,'Pad_Text',loops(b,'Sketch_TextOutline',polygons,orientation='XZ'),'TextThickness')
    return container


def sign_lettering(body):
    """Small per-glyph sketches drive one native Pocket with the exact slogan."""
    data=json.loads((LETTERING/'sign-lettering.json').read_text())
    body.addProperty('App::PropertyString','EngravedSlogan','Lettering')
    body.EngravedSlogan=data['slogan']
    sketches=[]
    longest=max(row['width_per_cap_height'] for row in data['lines'])
    top=f'(SignHeight+{longest:.12g}*SignTextHeight)/2'
    for index,row in enumerate(data['lines'],1):
        print(f'Building vertical sign phrase {index}/2: {row["text"]}',flush=True)
        origin=f'(SignWidth-2*SignTextHeight-SignColumnGap)/2+{index-1}*(SignTextHeight+SignColumnGap)'
        for glyph,indices in enumerate(row['glyphs'],1):
            polygons=[[(f'{origin}+({y:.12g})*SignTextHeight',f'{top}-({x:.12g})*SignTextHeight') for x,y in row['polygons'][i]] for i in indices]
            sketch=loops(body,f'Sketch_SignLine{index}_Glyph{glyph:02}',polygons,orientation='XZ')
            sketch.Label=f'凹刻轮廓 {index}.{glyph}: {row["text"]}'
            sketch.addProperty('App::PropertyInteger','SignLine','Lettering');sketch.SignLine=index
            sketches.append(sketch)
    return engrave_sign_sketches(body,sketches)


def engrave_sign_sketches(body,sketches):
    """Keep small sketches, then combine their planar wires for one native Pocket."""
    doc=body.Document;blank_volume=body.Shape.Volume
    area=sum(Part.makeFace(sketch.Shape.Wires,'Part::FaceMakerBullseye').Area for sketch in sketches)
    binder=body.newObject('PartDesign::SubShapeBinder','Binder_SignLettering')
    binder.Label=f'口号轮廓集合（{len(sketches)}个字形草图）'
    binder.Support=[(sketch,[]) for sketch in sketches]
    doc.recompute()
    feature=body.newObject('PartDesign::Pocket','Pocket_EngravedSlogan')
    feature.Label='完整口号凹刻 0.6 mm'
    feature.Profile=binder;feature.setExpression('Length',expression('SignEngraveDepth'));feature.Refine=True
    doc.recompute()
    expected=blank_volume-area*evaluate(doc,'SignEngraveDepth')
    # A binder's wire orientation determines its normal, rather than Sketch.Placement.
    if feature.Shape.isNull() or abs(feature.Shape.Volume-expected)>1e-4:
        feature.Reversed=True;doc.recompute()
    assert abs(feature.Shape.Volume-expected)<1e-4
    return finish(body,feature)
