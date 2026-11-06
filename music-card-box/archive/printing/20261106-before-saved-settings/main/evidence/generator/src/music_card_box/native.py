"""Small native Sketcher/PartDesign helpers. No project-external imports."""
import FreeCAD as App
import Part
import Sketcher
import re

def expression(text):
    return re.sub(r'(?<![.\w])([A-Z][A-Za-z0-9_]*)',r'Parameters.\1',str(text))

def value(doc, text):
    result=doc.Parameters.evalExpression(expression(text))
    return result.Value if hasattr(result,'Value') else float(result)

def plane(body, name, orientation='XZ', position=(0, 0, 0)):
    sketch = body.newObject('Sketcher::SketchObject', name)
    rotations = {'XY': App.Rotation(), 'XZ': App.Rotation(App.Vector(1,0,0),90),
                 'YZ': App.Rotation(App.Vector(1,1,1),120)}
    sketch.Placement = App.Placement(App.Vector(*position), rotations[orientation])
    return sketch

def polygon(body, name, points, orientation='XZ', position=(0,0,0)):
    sketch = plane(body, name, orientation, position)
    doc = body.Document
    for i, p in enumerate(points):
        q = points[(i+1) % len(points)]
        sketch.addGeometry(Part.LineSegment(App.Vector(value(doc,p[0]),value(doc,p[1]),0),
            App.Vector(value(doc,q[0]),value(doc,q[1]),0)),False)
    for i, p in enumerate(points):
        sketch.addConstraint(Sketcher.Constraint('Coincident',i,2,(i+1)%len(points),1))
        for axis, expression in zip(('X','Y'),p):
            index = sketch.addConstraint(Sketcher.Constraint('Distance'+axis,i,1,value(doc,expression)))
            sketch.setExpression(f'Constraints[{index}]', globals()['expression'](expression))
    doc.recompute()
    assert sketch.FullyConstrained, (name, sketch.SolverMessages if hasattr(sketch,'SolverMessages') else sketch.State)
    return sketch

def rectangle(body, name, x0, z0, x1, z1, **kwargs):
    return polygon(body,name,[(x0,z0),(x1,z0),(x1,z1),(x0,z1)],**kwargs)

def circles(body, name, items, position=(0,0,0)):
    sketch = plane(body,name,position=position)
    for x,z,radius in items:
        i = sketch.addGeometry(Part.Circle(App.Vector(x,z,0),App.Vector(0,0,1),radius),False)
        # Block is deliberately used for decorative circle positions only.
        # Functional shell dimensions remain expression-driven.
        sketch.addConstraint(Sketcher.Constraint('Block',i))
    body.Document.recompute()
    assert sketch.FullyConstrained
    return sketch

def finish(body, feature):
    body.Document.recompute()
    assert not feature.Shape.isNull() and feature.Shape.isValid(), (feature.Name,feature.State)
    assert len(feature.Shape.Solids)==1, (feature.Name,len(feature.Shape.Solids))
    for obj in body.Group:
        if obj.ViewObject: obj.ViewObject.Visibility = False
    if feature.ViewObject: feature.ViewObject.Visibility = True
    body.Tip = feature
    print('NATIVE',feature.Name,round(feature.Shape.Volume,3),flush=True)
    return feature

def feature(body, name, sketch, length, kind='Pad', reversed=True):
    result = body.newObject('PartDesign::'+kind, name)
    result.Profile = sketch
    result.setExpression('Length', expression(length))
    result.Reversed = reversed
    result.Refine = True
    return finish(body,result)

def fillet(body, name, indices, radius):
    assert indices, name
    previous = body.Tip
    result = body.newObject('PartDesign::Fillet',name)
    result.Base = (previous,['Edge'+str(i) for i in indices])
    result.Radius = radius
    return finish(body,result)

def edges_along_y(shape, predicate=lambda edge: True):
    indices=[]
    for i,e in enumerate(shape.Edges,1):
        b=e.BoundBox
        if b.YLength>0.1 and b.XLength<1e-5 and b.ZLength<1e-5 and predicate(e): indices.append(i)
    return indices
