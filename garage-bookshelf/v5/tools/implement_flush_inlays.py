"""Prepare a checked flush-inlay candidate without changing the current CAD."""
from pathlib import Path
import _bootstrap
import FreeCAD as App
import Part
from garage_bookshelf.paths import CAD, ROOT, sha, write_json
from garage_bookshelf.assembly import global_shape
from garage_bookshelf.flush_inlays import install
from implement_separate_skins import saved_views

out=ROOT/'build/flush-inlays-20261030'
source_hash=sha(CAD)
doc=App.openDocument(str(CAD))
old={b.SourcePart:global_shape(b) for b in doc.Objects if b.TypeId=='PartDesign::Body'}
skins,pockets=install(doc)
errors=[(o.Name,o.State) for o in doc.Objects if any(s in ('Invalid','Error') for s in o.State)]
assert not errors,errors
unchanged=[]
for name,shape in old.items():
    if name in ('module_2','module_3') or name.startswith('book_skin_'):continue
    new=global_shape(doc.getObject(name+'_Body'))
    error=shape.cut(new).Volume+new.cut(shape).Volume
    assert error<1e-6,(name,error)
    unchanged.append(name)
checks=[]
# The module-1 joint and side-sign mating areas are already committed to other prints.
for name,box in [('module_2',Part.makeBox(214-190,190,270,App.Vector(190,-10,-10))),
                 ('module_3',Part.makeBox(12,14,180,App.Vector(480,0,50)))]:
    new=global_shape(doc.getObject(name+'_Body'))
    difference=old[name].cut(new).common(box).Volume+new.cut(old[name]).common(box).Volume
    assert difference<1e-6,(name,difference)
    checks.append(dict(part=name,protected_interface_difference_mm3=difference))
for b in skins:
    box=global_shape(b).BoundBox
    front=box.YMin if b.SkinRole in ('Back','FrontEdge') else box.ZMax
    expected={'Back':159,'FrontEdge':0,'Floor':8,'TopRim':238}[b.SkinRole]
    assert abs(front-expected)<1e-6,(b.Name,front)
    thickness=box.YLength if b.SkinNormal.y else box.ZLength
    assert abs(thickness-.6)<1e-6,(b.Name,thickness)
    assert b.Shape.isValid() and len(b.Shape.Solids)==1,b.Name
    checks.append(dict(part=b.SourcePart,front_plane_mm=front,nominal_plane_mm=expected,thickness_mm=thickness))
for core in (doc.module_2_Body,doc.module_3_Body):
    assert core.Shape.isValid() and len(core.Shape.Solids)==1,core.Name
    new=global_shape(core)
    assert new.cut(old[core.SourcePart]).Volume<1e-6
    assert max(abs(getattr(new.BoundBox,k)-getattr(old[core.SourcePart].BoundBox,k)) for k in ('XMin','YMin','ZMin','XMax','YMax','ZMax'))<1e-6
candidate=out/CAD.name
doc.saveAs(str(candidate))
saved_views(CAD,candidate,doc,skins,{'module_2':'Black','module_3':'Black'})
App.closeDocument(doc.Name)
assert sha(CAD)==source_hash
write_json(out/'compatibility.json',dict(status='passed',previous_cad_sha256=source_hash,cad_sha256=sha(candidate),
  unchanged_bodies=unchanged,checks=checks,pockets=pockets,physical_print_and_fit_tested=False,
  manufacturing_mm=dict(inlay_thickness=.6,seat_depth=.6,glue_well_depth=.2,seat_width=1.5,side_clearance=.15,body_layer_height=.2),
  untouched_existing_3mf_files=True))
print('PASS candidate',candidate,flush=True)
