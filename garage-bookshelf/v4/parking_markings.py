"""Editable shallow parking engravings generated from the approved vector layout.

The source graphics have their origin at rear-left. Native deck sketches use
front-left, so y is reflected. Pattern dimensions follow DeckWidth/DeckDepth.
Only Sketch, SubShapeBinder and Pocket own the delivered CAD geometry.
"""
from functools import lru_cache
import FreeCAD as App
import Part
from decoration.generate import design, W, D, WHITE, YELLOW, ACCESS_BLUE, bay_width
from geometry.sketches import loops
from geometry.features import finish
from parameters import evaluate, expression

LAYOUTS = {1: 2, 2: 3, 3: 0}
PAINT = {'Blue':(.137,.416,.686), 'Yellow':(.953,.788,.271), 'White':(.969,.965,.925)}
SOURCE_COLORS = {'Blue':ACCESS_BLUE, 'Yellow':YELLOW, 'White':WHITE}


@lru_cache(None)
def outlines(count, color):
    solids=[]
    for item in design(count):
        if item['color']!=SOURCE_COLORS[color]:continue
        if item['kind']=='rect':
            x,y,w,h=[item[k] for k in ('x','y','w','h')]
            points=[(x,y),(x+w,y),(x+w,y+h),(x,y+h)]
        else:points=item['points']
        p=[App.Vector(x,D-y,0) for x,y in points]
        solids.append(Part.Face(Part.makePolygon(p+[p[0]])).extrude(App.Vector(0,0,1)))
    if not solids:return []
    union=solids[0].multiFuse(solids[1:]).removeSplitter() if len(solids)>1 else solids[0]
    faces=[f for f in union.Faces if abs(f.CenterOfMass.z-1)<1e-6 and f.normalAt(0,0).z>.99]
    return [[[(v.Point.x,v.Point.y) for v in wire.OrderedVertexes] for wire in face.Wires]
            for face in sorted(faces,key=lambda f:(f.CenterOfMass.x,f.CenterOfMass.y))]


def add(body, count):
    body.addProperty('App::PropertyInteger','ParkingBays','Parking layout');body.ParkingBays=count
    body.addProperty('App::PropertyString','ParkingLayout','Parking layout')
    body.ParkingLayout=f'{count} bay, {bay_width(count):g} x 90 mm'+(' / B01 wheelchair' if count==2 else '')
    body.addProperty('App::PropertyString','PaintNote','Parking layout')
    body.PaintNote='Pocket floor colours preview optional paint fill; print as one gray part.'
    for color in ('Blue','Yellow','White'):
        profiles=outlines(count,color)
        if not profiles:continue
        print(f'Parking {count} bay {color}: {len(profiles)} native profile islands',flush=True)
        sketches=[]
        for i,polygons in enumerate(profiles,1):
            scaled=[[(f'({x/W:.14g})*DeckWidth',f'({y/D:.14g})*DeckDepth') for x,y in polygon] for polygon in polygons]
            s=loops(body,f'Sketch_Parking{color}_{i:03}',scaled,offset=('Zero','Zero','DeckThickness'))
            s.addProperty('App::PropertyString','ParkingMarkingColor','Parking layout');s.ParkingMarkingColor=color
            sketches.append(s)
        binder=body.newObject('PartDesign::SubShapeBinder',f'Binder_Parking{color}')
        binder.Support=[(s,[]) for s in sketches]
        binder.addProperty('App::PropertyString','ParkingMarkingColor','Parking layout');binder.ParkingMarkingColor=color
        body.Document.recompute()
        f=body.newObject('PartDesign::Pocket',f'Pocket_Parking{color}')
        f.Label=f'停车图案凹刻 · {color}'
        f.Profile=binder
        f.setExpression('Length',expression('DeckBlueDepth' if color=='Blue' else 'DeckMarkingDepth'))
        f.Refine=True
        before=body.Shape.Volume
        finish(body,f)
        if f.Shape.Volume>=before-1e-5:
            f.Reversed=True;finish(body,f)
        assert f.Shape.Volume<before-1e-5
        for s in sketches:
            if s.ViewObject is not None:s.ViewObject.Visibility=False


def masks(body):
    """Planar color masks from saved native profiles, not transient shape files."""
    result={}
    for o in body.Group:
        if o.TypeId=='PartDesign::SubShapeBinder' and 'ParkingMarkingColor' in o.PropertiesList:
            result[o.ParkingMarkingColor]=Part.makeFace(o.Shape.Wires,'Part::FaceMakerBullseye')
    return result


def check(body):
    d=body.Document;count=LAYOUTS[int(body.SourcePart.rsplit('_',1)[1])]
    if not count:
        assert 'ParkingBays' not in body.PropertiesList
        return dict(bays=0,decoration='blank',removed_volume_mm3=0)
    assert body.ParkingBays==count
    planes=masks(body);t=evaluate(d,'DeckThickness')
    depths={key:evaluate(d,'DeckBlueDepth' if key=='Blue' else 'DeckMarkingDepth') for key in planes}
    cuts=[]
    for color,face in planes.items():
        assert abs(face.BoundBox.ZMin-t)<1e-5
        tool=face.extrude(App.Vector(0,0,-depths[color]))
        assert body.Shape.common(tool).Volume<1e-5
        cuts.append(tool)
    union=cuts[0].multiFuse(cuts[1:]).removeSplitter()
    base=next(o for o in body.Group if o.TypeId=='PartDesign::Pocket' and o.Name.startswith('Pocket_FourLocatingHoles'))
    removed=base.Shape.Volume-body.Shape.Volume
    assert abs(removed-union.Volume)<1e-4,(removed,union.Volume)
    # Check true material under the engraved floor, support pads, and all four holes.
    from build import CENTRES
    for cx,cy in CENTRES:
        x=evaluate(d,cx)-evaluate(d,'DeckEdgeGap');y=evaluate(d,cy)-evaluate(d,'DeckEdgeGap')
        keep=Part.makeCylinder(11,.5,App.Vector(x,y,t-.5))
        assert union.common(keep).Volume<1e-5
    minimum=t-max(depths.values())
    assert minimum>=4.6-1e-6
    return dict(bays=count,bay_nominal_mm=[bay_width(count),90],accessible_bay='B01' if count==2 else None,
                removed_volume_mm3=removed,minimum_remaining_thickness_mm=minimum,
                engraving_depth_mm=depths,independent_cut_volume_check='passed',
                column_keepout_radius_mm=11,paint_fill_preview_only=True)


def face_colors(body,base_color):
    planes=masks(body);d=body.Document;t=evaluate(d,'DeckThickness')
    result=[]
    for face in body.Shape.Faces:
        color=base_color
        if face.normalAt(0,0).z>.99:
            for name,mask in planes.items():
                depth=evaluate(d,'DeckBlueDepth' if name=='Blue' else 'DeckMarkingDepth')
                if abs(face.CenterOfMass.z-(t-depth))<1e-6:
                    projected=face.copy();projected.translate(App.Vector(0,0,depth))
                    if projected.common(mask).Area>face.Area*.99:
                        color=PAINT[name];break
        result.append(color)
    return result
