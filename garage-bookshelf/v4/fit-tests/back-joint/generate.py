import sys,json,math
from pathlib import Path
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as A,Part,MeshPart,Mesh
OUT=Path(__file__).resolve().parent/'artifacts';OUT.mkdir(exist_ok=True)
# Same 5 mm back, 8 mm base, 14 mm nominal male and 0.2 mm body fusion overlap as v4.
CASES=[('A',.4,1.,False),('B',.4,1.,True),('C',.4,.3,True),('D',.3,.3,True),('E',.2,.3,True),('F',.3,.2,True)]
GLYPHS={'A':['01110','10001','10001','11111','10001','10001','10001'],'B':['11110','10001','10001','11110','10001','10001','11110'],'C':['01111','10000','10000','10000','10000','10000','01111'],'D':['11110','10001','10001','10001','10001','10001','11110'],'E':['11111','10000','10000','11110','10000','10000','11111'],'F':['11111','10000','10000','11110','10000','10000','10000'],'M':['10001','11011','10101','10101','10001','10001','10001'],'S':['01111','10000','10000','01110','00001','00001','11110']}
def profile(x,c,tip=False):
 f=(10 if tip else 13)+c;r=(14 if tip else 17)+c
 pts=[A.Vector(x,-.2-c,30-f),A.Vector(x,-.2-c,30+f),A.Vector(x,5+c,30+r),A.Vector(x,5+c,30-r)]
 return Part.makePolygon(pts+[pts[0]])
def tool(x,c,length,corrected):
 a=Part.makeLoft([profile(x,c),profile(x+length,c,True)],True,False)
 if corrected:
  # Keep 14 mm mating taper; add end relief as a separate constant-section extrusion.
  ext=Part.Face(profile(x+14,c,True)).extrude(A.Vector(length-14,0,0))
  a=Part.makeLoft([profile(x,c),profile(x+14,c,True)],True,False).fuse(ext).removeSplitter()
 return a
def label(text):
 bits=[];pixel=.62
 for k,ch in enumerate(text):
  for row,line in enumerate(GLYPHS[ch]):
   for col,b in enumerate(line):
    if b=='1':bits.append(Part.makeBox(pixel+.015,pixel+.015,.4,A.Vector(2+k*6*pixel+col*pixel,-9+(6-row)*pixel,7.99)))
 return bits
male=Part.makeLoft([profile(17.8,0),profile(31.8,0,True)],True,False)
doc=A.newDocument('V4BackJointFitTests');records=[]
for idx,(tag,total,end,corrected) in enumerate(CASES):
 pair={}
 for sex,width in [('M',18),('S',24)]:
  body=Part.makeBox(width,17,8,A.Vector(0,-12,0)).fuse(Part.makeBox(width,5,52))
  body=body.fuse(male) if sex=='M' else body.cut(tool(-.2,total/2,14+end,corrected))
  for bit in label(tag+sex):body=body.fuse(bit)
  body=body.removeSplitter();assert body.isValid() and len(body.Solids)==1
  pair[sex]=body
  o=doc.addObject('PartDesign::Feature',tag+'_'+sex);o.Label=tag+'-'+sex;o.Shape=body
  o.addProperty('App::PropertyString','FitParameters');o.FitParameters=f'total side={total}; end={end}; corrected taper={corrected}'
  # Assembly CAD: pairs spaced along Y; male root shoulder x=18, socket shoulder x=18.
  o.Placement.Base=A.Vector(0 if sex=='M' else 18,idx*27,0)
  mesh=MeshPart.meshFromShape(Shape=body,LinearDeflection=.02,AngularDeflection=.12,Relative=False)
  mesh.translate(0,12,0)
  path=OUT/(tag+'-'+sex+'.stl');mesh.write(str(path));m=Mesh.Mesh(str(path))
  assert m.isSolid() and not m.hasNonManifolds()
 # Check closing path: no unintended interference, while shoulders meet at nominal position.
 path_checks=[]
 for delta in (20,10,5,1,0):
  socket=pair['S'].copy();socket.translate(A.Vector(18+delta,0,0))
  v=pair['M'].common(socket).Volume;assert v<1e-6,(tag,delta,v)
  path_checks.append({'separation_mm':delta,'overlap_mm3':v})
 records.append(dict(id=tag,total_nominal_side_clearance_mm=total,nominal_end_gap_mm=end,matched_axial_taper=corrected,closing_path=path_checks))
doc.recompute();doc.saveAs(str(OUT/'back-joint-fit-samples.FCStd'))
(OUT/'parameters.json').write_text(json.dumps(dict(cases=records,back_thickness_mm=5,base_thickness_mm=8,coupon_height_mm=52,male_nominal_length_mm=14,physical_fit='not_tested',scope='single back joint only; not a full module or base-joint test'),indent=2))
print('PASS 12 watertight coupons; 6 non-interfering closing paths',flush=True)
