# Frozen v4 source; use v5/tools or the migrated studies.
if __name__ == '__main__':
    raise SystemExit('Historical entry disabled; see v5/README.md and archive/README.md')

"""Proposed decorations on the current recessed decks; preview assets only.

Use FreeCAD's bundled Python. The formal FCStd and print deliveries are read-only.
Blank geometry and recess wires are read from that file; new paint is modeled
only in memory. Images are design proposals, not updated production CAD.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
sys.path.insert(0,str(ROOT))
import FreeCAD as App, Part
import numpy as np
from decoration.generate import design,lettering,wheelchair,W,D,WHITE,YELLOW,ACCESS_BLUE
from parameters import evaluate
from render_parking_recesses import render

RGB={WHITE:(.98,.975,.95),YELLOW:(.99,.76,.15),ACCESS_BLUE:(.12,.40,.74)}
GRAY=(.47,.51,.55)


def bay_edges(count,width):
    sx=width/W
    left=27.8*sx
    unit=48*sx
    return [left,left+2*unit,left+3*unit] if count==2 else [left+i*unit for i in range(4)]


def points(item):
    if item['kind']=='rect':
        x,y,w,h=[item[k] for k in ('x','y','w','h')]
        return [(x,y),(x+w,y),(x+w,y+h),(x,y+h)]
    return item['points']


def proposed(count,width,depth):
    sx,sy=width/W,depth/D
    polygons=[]
    edges=bay_edges(count,width)
    centers=[(a+b)/2 for a,b in zip(edges,edges[1:])]
    old_cx=27.8+72/2
    for item in design(count):
        xy=points(item);xs,ys=zip(*xy)
        if item['color']==ACCESS_BLUE:continue
        if item['color']==WHITE:
            if min(ys)>118.18 and max(ys)<122.23:continue
            if count==2 and min(xs)>old_cx-15 and max(xs)<old_cx+17 and min(ys)>50 and max(ys)<100:continue
            if count==2 and item['kind']=='rect' and abs(item['y']-25.2)<1e-6 and abs(item['h']-90.6)<1e-6:continue
        if count==2 and item['color']==YELLOW and item['kind']=='rect' and abs(item['y']-28.8)<1e-6 and abs(item['h']-2)<1e-6:continue
        polygons.append((item['color'],[(x*sx,depth-y*sy) for x,y in xy]))
    if count==2:
        for x in edges:
            polygons.append((WHITE,[(x-.6*sx,42.8),(x+.6*sx,42.8),
                                    (x+.6*sx,133.4),(x-.6*sx,133.4)]))
        for cx in centers:
            polygons.append((YELLOW,[(cx-10*sx,127.8),(cx+10*sx,127.8),
                                     (cx+10*sx,129.8),(cx-10*sx,129.8)]))
    # Floor-based IDs, moved 2 mm toward the front, away from finger notches.
    ids=[]
    for i in range(count):
        cx=centers[i]/sx
        lettering(ids,str(1 if count==2 else 2)+'0'+str(i+1),cx,120.2,4,WHITE)
    for item in ids:
        polygons.append((item['color'],[(x*sx,depth-y*sy) for x,y in points(item)]))
    if count==2:
        bay_left,bay_right=edges[:2];cx=centers[0]
        slot_left,slot_right=cx-20.3,cx+20.3
        for x0,x1 in [(bay_left+.6*sx,slot_left-1),(slot_right+1,bay_right-.6*sx)]:
            polygons.append((ACCESS_BLUE,[(x0,47.2),(x1,47.2),(x1,125.8),(x0,125.8)]))
        # 18 x 18 mm blue badge between crossing and direction arrow.
        polygons.append((ACCESS_BLUE,[(cx-9,11),(cx+9,11),(cx+9,29),(cx-9,29)]))
        symbol=[];wheelchair(symbol,0,0)
        for item in symbol:
            polygons.append((WHITE,[(cx+x*.46,20-y*.46) for x,y in points(item)]))
    return polygons


def mask(polygons,color,z):
    solids=[]
    for rgb,xy in polygons:
        if rgb!=color:continue
        p=[App.Vector(x,y,z) for x,y in xy]
        solids.append(Part.Face(Part.makePolygon(p+[p[0]])).extrude(App.Vector(0,0,1)))
    union=solids[0].multiFuse(solids[1:]).removeSplitter() if len(solids)>1 else solids[0]
    faces=[]
    for face in union.Faces:
        if abs(face.CenterOfMass.z-(z+1))<1e-6 and face.normalAt(0,0).z>.99:
            f=face.copy();f.translate(App.Vector(0,0,-1));faces.append(f)
    result=Part.makeCompound(faces)
    assert result.isValid()
    return result


def candidate(doc,level,count):
    body=doc.getObject(f'garage_deck_{level}_Body')
    t=evaluate(doc,'DeckThickness');w=evaluate(doc,'DeckWidth');d=evaluate(doc,'DeckDepth')
    # Native blank, including true hole positions, before historical decoration.
    base=next(o for o in body.Group if o.TypeId=='PartDesign::Pocket' and o.Name.startswith('Pocket_FourLocatingHoles'))
    shape=base.Shape.copy()
    corners=[e for e in shape.Edges if e.BoundBox.XLength<1e-6 and e.BoundBox.YLength<1e-6
             and abs(e.BoundBox.ZLength-t)<1e-6
             and min(abs(e.BoundBox.XMin),abs(e.BoundBox.XMin-w))<1e-6
             and min(abs(e.BoundBox.YMin),abs(e.BoundBox.YMin-d))<1e-6]
    assert len(corners)==4
    shape=shape.makeFillet(3,corners)
    sketch=next(o for o in body.Group if o.TypeId=='Sketcher::SketchObject' and o.Name.startswith('Sketch_ParkingTrayRecesses'))
    wires=[wire.copy() for wire in sorted(sketch.Shape.Wires,key=lambda p:p.BoundBox.Center.x)]
    if count==2:
        edges=bay_edges(count,w)
        for wire,cx in zip(wires,[(a+b)/2 for a,b in zip(edges,edges[1:])]):
            wire.translate(App.Vector(cx-wire.BoundBox.Center.x,0,0))
            assert abs(wire.BoundBox.XLength-evaluate(doc,'ParkingRecessWidth'))<1e-6
    outline=Part.makeCompound(wires)
    recess=Part.makeFace(wires,'Part::FaceMakerBullseye')
    shape=shape.cut(recess.extrude(App.Vector(0,0,-evaluate(doc,'ParkingRecessDepth')))).removeSplitter()
    entries=[]
    for edge in shape.Edges:
        bb=edge.BoundBox
        if abs(bb.ZMin-t)<1e-6 and abs(bb.ZMax-t)<1e-6:
            if edge.common(outline).Length>=edge.Length-1e-6:entries.append(edge)
    shape=shape.makeChamfer(evaluate(doc,'ParkingEntryChamfer'),entries)
    polygons=proposed(count,w,d)
    masks={}
    for color in (ACCESS_BLUE,YELLOW,WHITE):
        if not any(c==color for c,p in polygons):continue
        planar=mask(polygons,color,t)
        # Designs must stay entirely outside the load-bearing recess floors.
        assert planar.common(recess).Area<1e-6
        depth=.2 if color==ACCESS_BLUE else .4
        shape=shape.cut(planar.extrude(App.Vector(0,0,-depth))).removeSplitter()
        masks[color]=planar
    assert shape.isValid() and len(shape.Solids)==1
    paint=[]
    for face in shape.Faces:
        rgb=GRAY
        if face.normalAt(0,0).z>.99:
            if abs(face.CenterOfMass.z-(t-1.6))<1e-6:rgb=tuple(c*.84 for c in GRAY)
            for color,planar in masks.items():
                cut=.2 if color==ACCESS_BLUE else .4
                if abs(face.CenterOfMass.z-(t-cut))<1e-6:
                    p=face.copy();p.translate(App.Vector(0,0,cut))
                    if p.common(planar).Area>face.Area*.99:rgb=RGB[color];break
        paint.append(rgb)
    return shape,paint


def tessellate(shape,paint):
    light=np.array([-.45,-.65,.85]);light/=np.linalg.norm(light)
    p,colors=[],[]
    for face,rgb in zip(shape.Faces,paint):
        vertices,indices=face.tessellate(.08)
        if not indices:continue
        v=np.array([[p.x,p.y,p.z] for p in vertices]);tri=v[np.array(indices)]
        normal=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])
        normal/=np.maximum(np.linalg.norm(normal,axis=1)[:,None],1e-12)
        shade=.72+.28*np.abs(normal@light)
        p.extend(tri);colors.extend(np.array(rgb)[None,:]*shade[:,None])
    return np.array(p),np.array(colors)


def main():
    source=ROOT/'garage-bookshelf-v4-assembly.FCStd'
    before=hashlib.sha256(source.read_bytes()).hexdigest()
    doc=App.openDocument(str(source));records=[]
    for level,count in [(1,2),(2,3)]:
        print('Building proposed',count,'bay preview',flush=True)
        shape,colors=candidate(doc,level,count)
        pts,paint=tessellate(shape,colors)
        path=OUT/f'proposed-{count}-bay.png'
        record=render(pts,paint,path,[-.65,-1.9,3.8],width=1600,height=1250)
        record.update(bays=count,proposal_only=True,geometry_valid=True,
                      recess_floor_thickness_mm=5,ids_moved_toward_front_mm=2)
        edges=bay_edges(count,evaluate(doc,'DeckWidth'))
        record.update(bay_widths_mm=[round(b-a,3) for a,b in zip(edges,edges[1:])],
                      accessible_bay='left' if count==2 else None,
                      tray_recess_dimensions_mm=[40.6,80.6])
        records.append(record)
        print('Rendered',path,flush=True)
    App.closeDocument(doc.Name)
    assert hashlib.sha256(source.read_bytes()).hexdigest()==before
    (OUT/'preview-validation.json').write_text(json.dumps(dict(
        status='passed',source_cad_sha256=before,formal_cad_modified=False,
        print_files_modified=False,proposals=records),indent=2)+'\n')


if __name__=='__main__':main()
