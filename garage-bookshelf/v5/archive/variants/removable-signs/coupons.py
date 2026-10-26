# Frozen v4 source; use v5/tools or the migrated studies.
if __name__ == '__main__':
    raise SystemExit('Historical entry disabled; see v5/README.md and archive/README.md')

"""Small coupon with the exact receiver and rail cross sections, plus a blank side insert."""
import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('retrofit',ROOT/'build.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
from parameters import create
from assembly import group,part,global_shape
from geometry.sketches import rectangle
from geometry.features import pad
import FreeCAD as A,Part,MeshPart,Mesh,json

def export(shape,name):
    mesh=MeshPart.meshFromShape(Shape=shape,LinearDeflection=.02,AngularDeflection=.12,Relative=False)
    mesh.transform(A.Placement(A.Vector(),A.Rotation(A.Vector(1,0,0),90)).toMatrix());bb=mesh.BoundBox;mesh.translate(-bb.XMin,-bb.YMin,-bb.ZMin)
    assert mesh.isSolid() and not mesh.hasNonManifolds();mesh.write(str(ROOT/'print-stl'/f'{name}.stl'))
d=A.newDocument('FitCoupon');create(d);g=group(d,'Coupon','先打印：燕尾试配件')
_,a=part(d,g,'fit_receiver','试配母槽');pad(a,'Pad_Base',rectangle(a,'Sketch_Base','40 mm','4 mm'),'28 mm');m.rail(a,'TestSlot',14,4.7,35.5,female=True)
_,b=part(d,g,'fit_carrier','试配公轨',('5 mm','Zero','4 mm'));pad(b,'Pad_Carrier',rectangle(b,'Sketch_Carrier','30 mm','20 mm',orientation='XZ',offset=('Zero','CarrierBack','Zero')),'1.8 mm');m.rail(b,'TestRail',10,0,30)
assert global_shape(a).common(global_shape(b)).Volume<.01
for off in [41,30,10,0]:
 s=global_shape(b);s.translate(A.Vector(off,0,0));assert s.common(global_shape(a)).Volume<.01
for name,body in [('fit_receiver',a),('fit_carrier',b)]:export(body.Shape,name)
d.saveAs(str(ROOT/'fit-test.FCStd'))
d=A.openDocument(str(ROOT/'removable-signs-assembly.FCStd'))
b=d.side_cartridge_Body
feature=next(o for o in b.Group if o.Name.startswith('Pad_SideRail38'))
blank=feature.Shape.cut(Part.makeCylinder(1.65,1.8,A.Vector(24,-2,12),A.Vector(0,1,0)))
export(blank,'side_cartridge_blank')
(ROOT/'reports/fit-test.json').write_text(json.dumps(dict(status='passed',same_cross_section_as_both_signs=True,physical_fit='not_tested',female_size_mm=[40,28,4],male_plate_size_mm=[30,20,1.8]),indent=2))
print('PASS fit coupon and blank side insert')
