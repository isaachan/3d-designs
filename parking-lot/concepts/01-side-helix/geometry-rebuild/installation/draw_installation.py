#!/usr/bin/env python3
"""Draw mounting studies from shared BRep parts, with real bores and seats."""
import sys, math, json
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent))
import build_geometry as b
import mount_parts as m
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy
from PIL import Image, ImageDraw, ImageFont

FONT='/System/Library/Fonts/STHeiti Medium.ttc'
INK=(30,45,55); MUTED=(83,102,112); PAPER=(248,248,246)
RED=(176,50,56); GRAY=(.44,.49,.52); WHITE=(.92,.94,.95)
def ft(n): return ImageFont.truetype(FONT,n)


def as_actor(shape,color):
    pts,fs=shape.tessellate(.09); mesh=b.Mesh()
    for f in fs: mesh.face([(pts[i].x,pts[i].y,pts[i].z) for i in f],color)
    p=mesh.polydata(); mapper=vtk.vtkPolyDataMapper(); mapper.SetInputData(p); mapper.ScalarVisibilityOff()
    a=vtk.vtkActor(); a.SetMapper(mapper); a.GetProperty().SetColor(color); a.GetProperty().SetAmbient(.32); a.GetProperty().SetDiffuse(.68); a.GetProperty().SetSpecular(.18); a.GetProperty().SetSpecularPower(30)
    return a


def render(actors,toward=(-1,-2,1),size=(1400,1000),fit=.88):
    r=vtk.vtkRenderer(); r.SetBackground(*(v/255 for v in PAPER)); r.SetUseFXAA(True)
    for a in actors: r.AddActor(a)
    for pos,intensity in [((-200,-350,450),.95),((300,200,250),.55)]:
        l=vtk.vtkLight(); l.SetLightTypeToSceneLight(); l.SetPosition(*pos); l.SetFocalPoint(-30,0,-10); l.SetIntensity(intensity); r.AddLight(l)
    to=np.array(toward,dtype=float); to/=np.linalg.norm(to)
    up0=np.array([0,0,1.]); right=np.cross(up0,to); right/=np.linalg.norm(right); up=np.cross(to,right)
    cloud=np.concatenate([vtk_to_numpy(a.GetMapper().GetInput().GetPoints().GetData()) for a in actors])
    p=cloud@np.stack([right,up,to],axis=1); low,high=p.min(axis=0),p.max(axis=0); mid=(low+high)/2
    focal=mid[0]*right+mid[1]*up+mid[2]*to
    cam=r.GetActiveCamera(); cam.ParallelProjectionOn(); cam.SetFocalPoint(*focal); cam.SetPosition(*(focal+1000*to)); cam.SetViewUp(0,0,1)
    w,h=size; cam.SetParallelScale(max((high[1]-low[1])/2,(high[0]-low[0])*h/(2*w))/fit)
    win=vtk.vtkRenderWindow(); win.SetOffScreenRendering(1); win.SetSize(w,h); win.SetMultiSamples(8); win.AddRenderer(r); r.ResetCameraClippingRange(); win.Render()
    capture=vtk.vtkWindowToImageFilter(); capture.SetInput(win); capture.SetInputBufferTypeToRGB(); capture.ReadFrontBufferOff(); capture.Update()
    a=vtk_to_numpy(capture.GetOutput().GetPointData().GetScalars()).reshape(h,w,3)
    image=Image.fromarray(np.flipud(a).copy())
    def point(v):
        r.SetWorldPoint(*v,1); r.WorldToDisplay(); x,y,_=r.GetDisplayPoint(); return np.array([x,h-y])
    # Project supplied anchors before finalizing the window in the caller.
    return image,point,win


def title(canvas,a,c):
    d=ImageDraw.Draw(canvas); d.text((60,32),a,font=ft(40),fill=INK); d.text((60,92),c,font=ft(25),fill=MUTED)


def note(draw,anchor,text,at,color=INK):
    x,y=at; lines=text.split('\n'); widths=[draw.textbbox((0,0),s,font=ft(24))[2] for s in lines]
    w=max(widths)+22; h=33*len(lines)+14
    draw.rectangle((x-10,y-5,x+w,y+h),fill=PAPER)
    edge=np.array([x+w/2,y+h/2]); target=np.array(anchor)
    # Start the leader at the side closest to its target.
    if target[0]<x: edge[0]=x-10
    elif target[0]>x+w: edge[0]=x+w
    draw.line([tuple(edge),tuple(target)],fill=color,width=2)
    draw.ellipse((target[0]-4,target[1]-4,target[0]+4,target[1]+4),fill=color)
    for i,s in enumerate(lines): draw.text((x,y+i*33),s,font=ft(24),fill=color)


def snapshot_4f():
    b.SCENE.clear(); poly,ts,_=b.road_geometry(); colors=vtk_to_numpy(poly.GetCellData().GetScalars()); wanted=np.round(np.array(b.RED)*255)
    ids=vtk.vtkIdTypeArray()
    for i in range(poly.GetNumberOfCells()):
        cell=poly.GetCell(i); z=[poly.GetPoint(cell.GetPointId(j))[2] for j in range(cell.GetNumberOfPoints())]
        if np.array_equal(colors[i],wanted) or (min(z)>190 and np.array_equal(colors[i],np.round(np.array(b.GRAY)*255))): ids.InsertNextValue(i)
    sel=vtk.vtkSelectionNode(); sel.SetFieldType(vtk.vtkSelectionNode.CELL); sel.SetContentType(vtk.vtkSelectionNode.INDICES); sel.SetSelectionList(ids)
    selection=vtk.vtkSelection(); selection.AddNode(sel)
    extract=vtk.vtkExtractSelection(); extract.SetInputData(0,poly); extract.SetInputData(1,selection); extract.Update()
    surf=vtk.vtkGeometryFilter(); surf.SetInputConnection(extract.GetOutputPort()); surf.Update()
    actors=[b.actor(surf.GetOutput(),b.BLACK,'detail','4F-road')]
    b.curbs(ts)
    actors.extend(a for a,cat,name in b.SCENE if cat=='curb' and (name=='curb-2' or name=='bridge-rail-3' or (name=='end-stop' and a.GetBounds()[4]>190)))
    actors.append(as_actor(m.box(0,200,0,230,190.4,197),b.BLACK))
    image,point,win=render(actors,(-1.1,-1.9,1.5),(1800,1080),.80)
    canvas=Image.new('RGB',(1800,1350),PAPER); canvas.paste(image,(0,150)); d=ImageDraw.Draw(canvas)
    title(canvas,'4F 终点收齐｜去掉接入口旁的多余死端','70 mm 出口保留；前缘收口到 Y=40，与停车通道前缘齐平。')
    def p(v): return point(v)+[0,150]
    old=[]; end=math.pi+3*math.tau
    for r,t in [(155,end+b.ALPHA)]+[(155,t) for t in np.linspace(end+b.ALPHA,end+b.LANDING,30)]+[(85,end+b.LANDING),(85,end+math.asin(35/85))]:
        old.append(p(b.polar(r,t,197)))
    for i in range(len(old)-1):
        a,c=old[i],old[i+1]; length=np.linalg.norm(c-a)
        for k in np.arange(0,length,15):
            f=min((k+8)/max(length,1e-6),1); d.line([tuple(a+(c-a)*k/max(length,1e-6)),tuple(a+(c-a)*f)],fill=RED,width=4)
    note(d,p((302,40,201)),'当前收口线\n不再向前伸出',(1050,1040))
    note(d,p(b.polar(145,end+b.LANDING,197)),'红色虚线范围\n是已删除的死端',(1180,1150),RED)
    d.text((60,1294),'局部剥离：显示最后一圈和 4F 停车板；3F 停车板已隐藏。主坡道仍为 70 mm 净宽。',font=ft(24),fill=MUTED)
    canvas.save(ROOT/'12-4f-terminal-detail.png'); win.Finalize()


def location_map():
    b.SCENE.clear(); poly,ts,_=b.road_geometry(); b.actor(poly,b.BLACK,'road','road'); b.curbs(ts); b.parking_and_signs(); b.arrows()
    actors=[]
    for a,cat,name in b.SCENE:
        if cat not in ('support','base'):
            a.GetProperty().SetColor(.75,.79,.81); a.GetProperty().SetOpacity(.24)
        actors.append(a)
    image,point,win=render(actors,(-1.1,-2.4,1.3),(1800,1120),.79)
    canvas=Image.new('RGB',(1800,1400),PAPER); canvas.paste(image,(0,140)); d=ImageDraw.Draw(canvas)
    title(canvas,'黑色支撑安装位置｜A 车库四柱 / B 坡道三柱 / C 侧牌立杆','A 沿用分段销＋托环；B 采用定位肩＋两半抱箍；B/C 底部用法兰固定。')
    def p(v): return point(v)+[0,140]
    note(d,p((12,14,115)),'A · 车库四柱\n分段叠装，托环承重',(60,400))
    for i,deg in enumerate((35,95,275)):
        t=math.radians(deg); pos=(b.CX+169*math.cos(t),b.CY+169*math.sin(t),150 if i<2 else 100)
        at=[(1380,360),(760,185),(1380,1000)][i]
        note(d,p(pos),f'B{i+1} · 外侧坡道柱\n每柱 3 只可拆托臂',at)
    note(d,p((602,74,85)),'C · 侧牌立杆\n底法兰与 B 相同',(1430,690))
    d.text((60,1330),'图中灰色半透明部分为定位参照；所有黑色安装件都在车道净宽之外或路板下方。',font=ft(24),fill=MUTED)
    canvas.save(ROOT/'13-support-location.png'); win.Finalize()


def exploded(parts,post,theta):
    actors=[]; shifted={}
    for item in parts:
        s=item['shape'].copy(); offset=m.V(item['explode']); s.translate(offset)
        a=as_actor(s,item['color'])
        if item['role']=='road': a.GetProperty().SetOpacity(.38)
        actors.append(a); shifted[item['name']]=offset
    local=post.copy(); local.translate(m.V(0,0,-b.height(theta)))
    local=local.common(m.box(-16,16,-20,20,-45,18)); actors.append(as_actor(local,GRAY))
    image,point,win=render(actors,(1.3,-2.7,1.15),(1800,1120),.76)
    canvas=Image.new('RGB',(1800,1420),PAPER); canvas.paste(image,(0,140)); d=ImageDraw.Draw(canvas)
    title(canvas,'B · 坡道托臂分解安装','托臂内半箍与梁一体；外半箍从柱外侧合上，无需把整圈轨道套过立柱。')
    def p(v): return point(v)+[0,140]
    note(d,p((-24,0,13)),'① 从轨道下侧装入\n2 只 M3 短热熔螺母',(60,230))
    note(d,p((-45,0,-10)),'② 轨道先临时垫高 2 mm\n托臂从柱侧装到柱肩上',(60,870))
    note(d,p((30,0,-11.6)),'③ 从外侧合上半箍\n2 颗 M3×16＋螺母',(1330,380))
    note(d,p((-24,0,-35)),'④ 从下方拧入\n2 颗 M3×10＋垫片',(1120,1120))
    note(d,p((-8.2,0,-16.6)),'定位肩承受竖向载荷\n抱箍负责夹紧和定位',(60,1145))
    d.text((60,1355),'外半箍装好后，抽去临时垫片让轨道落座，再拧下方螺钉。轨道半透明，螺纹简化。',font=ft(24),fill=MUTED)
    canvas.save(ROOT/'14-ramp-mount-exploded.png'); win.Finalize()


def sections(parts,post,theta):
    canvas=Image.new('RGB',(1800,1350),PAPER); d=ImageDraw.Draw(canvas)
    title(canvas,'B · 两个关键剖面','左：螺钉不穿出路面。右：托臂落在定位肩上，不靠摩擦悬挂。')
    views=[]
    cut=m.box(-24,-11,-15,15,-25,3)
    wanted={'road','arm','insert','road-bolt','road-washer'}
    actors=[]
    for item in parts:
        if item['role'] not in wanted: continue
        s=item['shape'].common(cut)
        if not s.isNull() and s.Volume>1e-6: actors.append(as_actor(s,item['color']))
    im,project,win=render(actors,(-1,-.55,.32),(850,870),.75); canvas.paste(im,(35,235))
    def left(v): return project(v)+[35,235]
    d.text((70,175),'B-1 · 轨道—托臂固定剖面',font=ft(28),fill=INK)
    note(d,left((-24,-.4,-4)),'热熔螺母长 4 mm\n盲孔深 5 mm',(65,230))
    note(d,left((-24,0,-1.4)),'路板厚 6.6 mm\n顶面余厚约 1.6 mm',(65,1050))
    note(d,left((-24,1,-13)),'M3×10 从下方拧入',(430,1160))
    local=post.copy(); local.translate(m.V(0,0,-b.height(theta)))
    cut2=m.box(-20,15,0,18,-25,0); actors=[]
    for s,c in [(local,GRAY)]+[(p['shape'],p['color']) for p in parts if p['role'] in ('arm','cap')]:
        s=s.common(cut2)
        if not s.isNull() and s.Volume>1e-6: actors.append(as_actor(s,c))
    im,p2,w2=render(actors,(.15,-1,.22),(850,870),.76); canvas.paste(im,(915,235))
    def right(v): return p2(v)+[915,235]
    d.text((965,175),'B-2 · 抱箍—立柱承托剖面',font=ft(28),fill=INK)
    note(d,right((0,0,-5)),'立柱 Ø14\n抱箍孔 Ø14.4',(1390,230))
    a,c=right((-9,0,-16.6)),right((-7.2,0,-16.6)); d.line([tuple(a),tuple(c)],fill=RED,width=6)
    note(d,(a+c)/2,'红线：承托接触面\n定位肩与立柱一体打印',(955,1080),RED)
    d.text((60,1297),'配合间隙为方案值；热熔孔与抱箍需按实际材料、嵌件和打印收缩做试装。',font=ft(24),fill=MUTED)
    canvas.save(ROOT/'15-ramp-mount-sections.png'); win.Finalize(); w2.Finalize()


def base_and_garage(post):
    canvas=Image.new('RGB',(1800,1450),PAPER); d=ImageDraw.Draw(canvas)
    title(canvas,'底座固定与车库柱安装','B/C：法兰螺栓固定。A：沿用 garage 的定位销、托环和柱底盲孔。')
    plate=m.box(-23,23,-26,26,0,1.3).fuse(m.base_pad())
    for v in [-10.5,10.5]: plate=plate.cut(m.Part.makeCylinder(1.7,5,m.V(0,v,-3)))
    actors=[as_actor(plate,(.35,.40,.44))]
    lower=post.common(m.box(-20,20,-20,20,-10,36)); lower.translate(m.V(0,0,22)); actors.append(as_actor(lower,m.BLACK))
    for item in m.foot_hardware():
        s=item['shape'].copy(); dz=40 if item['role']=='foot-bolt' or 'top_washer' in item['name'] else -14
        s.translate(m.V(0,0,dz)); actors.append(as_actor(s,item['color']))
    image,p,win=render(actors,(1.0,-1.7,1.0),(850,890),.75); canvas.paste(image,(35,235))
    def q(v):return p(v)+[35,235]
    d.text((70,175),'B/C · 底法兰固定（分解）',font=ft(28),fill=INK)
    note(d,q((11,0,24)),'立柱与 Ø28 法兰一体\n法兰厚 3 mm',(65,240))
    note(d,q((0,10.5,20)),'2 颗 M3×10\n上下均加垫片',(505,740))
    note(d,q((0,-10.5,-12)),'底面用六角螺母锁紧\n脚垫留出 6 mm 空间',(65,1100))
    low=m.garage_segment(0); floor=m.garage_floor(63); upper=m.garage_segment(63)
    crop=m.box(-25,25,0,24,-2,84)
    low=low.common(crop); pin=m.cyl(3,56.4,66).common(crop); low=low.cut(pin)
    floor=floor.common(crop); floor.translate(m.V(0,0,14))
    upper=upper.common(m.box(-25,25,0,24,63,83)); upper.translate(m.V(0,0,30))
    image,p2,w2=render([as_actor(low,m.BLACK),as_actor(pin,(.19,.64,.81)),as_actor(floor,(.27,.47,.58)),as_actor(upper,m.BLACK)],(.25,-1,.35),(850,890),.74)
    canvas.paste(image,(915,235))
    def r(v):return p2(v)+[915,235]
    d.text((965,175),'A · 分段车库柱（半剖分解）',font=ft(28),fill=INK)
    note(d,r((0,0,95)),'上段柱底 Ø6.5 盲孔\n深 3.3 mm',(1340,250))
    note(d,r((7,0,75)),'层板厚 6.6 mm\n穿孔 Ø6.5',(1480,600))
    note(d,r((0,0,62)),'定位销 Ø6\n穿过层板后露出 3 mm',(955,900))
    note(d,r((9,0,54.4)),'Ø20 × 4 托环承重\n下方为 45° 锥肩',(1300,1120))
    d.text((60,1355),'安装顺序：底座与柱 → 下段承托 → 放层板 → 插上段柱；坡道托臂再从柱侧装上。',font=ft(24),fill=INK)
    d.text((60,1400),'蓝色定位销仅作高亮，实际与下段柱一体；销孔配合沿用 garage-bookshelf v5，需试装。',font=ft(24),fill=MUTED)
    canvas.save(ROOT/'16-base-and-garage-installation.png'); win.Finalize(); w2.Finalize()


def main():
    theta=math.radians(275)+math.tau
    heights=[b.height(theta+(k-1)*math.tau) for k in range(3)]
    post=m.upright(heights); parts=m.station(theta,b.height)
    checks=m.interference_checks(parts,post,b.height(theta))
    snapshot_4f(); print('12 rendered',flush=True)
    location_map(); print('13 rendered',flush=True)
    exploded(parts,post,theta); print('14 rendered',flush=True)
    sections(parts,post,theta); print('15 rendered',flush=True)
    base_and_garage(post); print('16 rendered',flush=True)
    doc=m.App.newDocument('ParkingLotMountStudy')
    for p in parts:
        obj=doc.addObject('PartDesign::Feature',p['name']); obj.Label=p['name']; obj.Shape=p['shape']
    upright=doc.addObject('PartDesign::Feature','Upright'); upright.Shape=post.copy(); upright.Placement.Base=m.V(0,0,-b.height(theta))
    doc.recompute(); doc.saveAs(str(ROOT/'mounting-study.FCStd'))
    m.Part.export(doc.Objects,str(ROOT/'mounting-study.step')); m.App.closeDocument(doc.Name)
    arm=next(p['shape'] for p in parts if p['role']=='arm'); cap=next(p['shape'] for p in parts if p['role']=='cap')
    local=post.copy(); local.translate(m.V(0,0,-b.height(theta)))
    report=dict(brep_solids_valid=True,station_parts=len(parts),interferences=checks,arm_to_seat_distance_mm=arm.distToShape(local)[0],cap_to_seat_distance_mm=cap.distToShape(local)[0],post_diameter_mm=14,clamp_bore_mm=14.4,garage_pin_mm=6,garage_hole_mm=6.5,temporary_track_lift_mm=2,base_screw_clearance_to_floor_mm=.8,insert='RX-M3Sx4.0 or dimensionally equivalent, pilot 4 x depth 5',status='Proposed assembly; fit and load tests pending')
    assert report['arm_to_seat_distance_mm']<1e-6 and report['cap_to_seat_distance_mm']<1e-6
    (ROOT/'mounting-checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__': main()
