"""Global placement lives on assembly containers; Body sketches use local coordinates."""
import FreeCAD as App
from parameters import expression
COLORS={'modules':(.55,.58,.62),'garage':(.55,.58,.62),'columns':(.98,.72,.10),'sign':(.10,.36,.88),'billboard':(.08,.09,.11),'text':(.95,.95,.95)}

def group(doc,name,label):
    p=doc.addObject('App::Part',name);p.Label=label;return p

def part(doc,parent,name,label,position=('Zero','Zero','Zero'),rotation=None,color='modules',body=True):
    p=group(doc,name,label);parent.addObject(p)
    for axis,val in zip('xyz',position):p.setExpression('Placement.Base.'+axis,expression(val))
    if rotation:p.Placement.Rotation=rotation
    p.addProperty('App::PropertyString','SourcePart','Design reference');p.SourcePart=name
    if not body:return p,None
    b=doc.addObject('PartDesign::Body',name+'_Body');b.Label=label+' · Body';p.addObject(b)
    b.addProperty('App::PropertyString','SourcePart','Design reference');b.SourcePart=name
    if b.ViewObject is not None:b.ViewObject.ShapeColor=COLORS[color]
    return p,b

def global_shape(body):
    s=body.Shape.copy();s.Placement=body.getGlobalPlacement().multiply(body.Placement.inverse()).multiply(s.Placement);return s

def parts(doc):
    return {p.SourcePart:p for p in doc.Objects if p.TypeId=='App::Part' and 'SourcePart' in p.PropertiesList}

def bodies(part):
    return [o for o in part.Group if o.TypeId=='PartDesign::Body']
