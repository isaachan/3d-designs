"""Fully dimensional native sketches, without fixed geometry or face-number links."""
import FreeCAD as App
import Part, Sketcher
from parameters import expression, evaluate

ROTATIONS={'XY':App.Rotation(),'YZ':App.Rotation(App.Vector(1,1,1),120),'XZ':App.Rotation(App.Vector(1,0,0),90)}

def plane(body,name,orientation='XY',offset=('Zero','Zero','Zero')):
    s=body.newObject('Sketcher::SketchObject',name)
    s.Placement.Rotation=ROTATIONS[orientation]
    for axis,val in zip('xyz',offset): s.setExpression('Placement.Base.'+axis,expression(val))
    return s

def loops(body,name,polygons,orientation='XY',offset=('Zero','Zero','Zero')):
    s=plane(body,name,orientation,offset);d=body.Document
    for points in polygons:
        first=s.GeometryCount;n=len(points)
        for i,p in enumerate(points):
            q=points[(i+1)%n]
            s.addGeometry(Part.LineSegment(App.Vector(evaluate(d,p[0]),evaluate(d,p[1]),0),App.Vector(evaluate(d,q[0]),evaluate(d,q[1]),0)),False)
        for i,p in enumerate(points):
            j=first+i;s.addConstraint(Sketcher.Constraint('Coincident',j,2,first+(i+1)%n,1))
            for axis,val in zip(('X','Y'),p):
                c=s.addConstraint(Sketcher.Constraint('Distance'+axis,j,1,evaluate(d,val)))
                s.setExpression(f'Constraints[{c}]',expression(val))
    d.recompute()
    if not s.FullyConstrained or 'Invalid' in s.State: raise RuntimeError(f'{s.Name}: sketch not fully constrained: {s.State}')
    return s

def rectangle(body,name,width,depth,origin=('Zero','Zero'),**kw):
    x,y=origin
    return loops(body,name,[[(x,y),(f'{x}+({width})',y),(f'{x}+({width})',f'{y}+({depth})'),(x,f'{y}+({depth})')]],**kw)

def circle(body,name,radius,z,center=('Zero','Zero')):
    s=plane(body,name,offset=('Zero','Zero',z));d=body.Document
    s.addGeometry(Part.Circle(App.Vector(evaluate(d,center[0]),evaluate(d,center[1]),0),App.Vector(0,0,1),evaluate(d,radius)),False)
    for axis,val in zip(('X','Y'),center):
        c=s.addConstraint(Sketcher.Constraint('Distance'+axis,0,3,evaluate(d,val)));s.setExpression(f'Constraints[{c}]',expression(val))
    c=s.addConstraint(Sketcher.Constraint('Radius',0,evaluate(d,radius)));s.setExpression(f'Constraints[{c}]',expression(radius))
    d.recompute()
    if not s.FullyConstrained:raise RuntimeError(f'{s.Name}: underconstrained circle')
    return s
