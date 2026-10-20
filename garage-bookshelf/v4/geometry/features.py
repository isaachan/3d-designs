"""Only native Part Design features own final geometry."""
from parameters import expression

def finish(body,feature):
    body.Document.recompute()
    if feature.Shape.isNull() or not feature.Shape.isValid() or len(feature.Shape.Solids)!=1 or 'Invalid' in feature.State:
        raise RuntimeError(f'{body.Name}/{feature.Name}: invalid feature ({feature.State})')
    for o in body.Group:
        if o.ViewObject is not None:o.ViewObject.Visibility=False
    if feature.ViewObject is not None:feature.ViewObject.Visibility=True
    body.Tip=feature
    return feature

def pad(body,name,sketch,length):
    f=body.newObject('PartDesign::Pad',name);f.Profile=sketch;f.setExpression('Length',expression(length));f.Refine=True
    return finish(body,f)

def pocket(body,name,sketch,length):
    f=body.newObject('PartDesign::Pocket',name);f.Profile=sketch;f.setExpression('Length',expression(length));f.Refine=True
    return finish(body,f)

def loft(body,name,root,tip,subtract=False):
    f=body.newObject('PartDesign::SubtractiveLoft' if subtract else 'PartDesign::AdditiveLoft',name)
    f.Profile=root;f.Sections=[tip];f.Ruled=False;f.Refine=True
    return finish(body,f)
