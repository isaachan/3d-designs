#!/usr/bin/env python3
"""Build and render actual constant-width concept geometry; no image inputs.

Run with /Applications/FreeCAD.app/Contents/Resources/bin/python.
Units are millimetres. This is a geometric study, not a printing model.
"""
import json
import math
import sys
from pathlib import Path
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'installation'))
sys.path.insert(0,str(ROOT/'installation'/'column-reuse'))
import column_parts as mounts
TAU = math.tau
CX, CY = 410., 75.
RI, RO, PITCH, THICK = 85., 155., 63., 6.6
BRIDGE_X, HALF_W, LANDING = 200., 35., math.radians(25)
ALPHA = math.asin(HALF_W / RO)
Z0 = 8.
BLACK = (.095, .11, .13)
CYAN, BLUE, RED = (.15, .65, .84), (.11, .15, .40), (.89, .13, .17)
WHITE, GRAY = (.93, .95, .96), (.46, .53, .57)
COLORS = [CYAN, BLUE, RED]
SCENE = []
TERMINAL_Y = CY-HALF_W


def clip_terminal(vertices):
    """Clip the unused 4F tail to the front edge of its 70-mm exit."""
    out=[]
    for a,b in zip(vertices,vertices[1:]+vertices[:1]):
        a,b=np.array(a,dtype=float),np.array(b,dtype=float)
        ia,ib=a[1]>=TERMINAL_Y-1e-9,b[1]>=TERMINAL_Y-1e-9
        if ia: out.append(tuple(a))
        if ia!=ib:
            t=(TERMINAL_Y-a[1])/(b[1]-a[1]); v=a+t*(b-a); v[1]=TERMINAL_Y; out.append(tuple(v))
    cleaned=[]
    for x,y,z in out:
        v=(x,TERMINAL_Y if abs(y-TERMINAL_Y)<1e-7 else y,z)
        if not cleaned or np.linalg.norm(np.array(v)-cleaned[-1])>1e-8: cleaned.append(v)
    if len(cleaned)>1 and np.linalg.norm(np.array(cleaned[0])-cleaned[-1])<1e-8: cleaned.pop()
    return cleaned if len(cleaned)>=3 else []


def rise(u):
    a, b, e = LANDING, TAU - LANDING, math.radians(15)
    run, t = b-a, u*TAU-a
    if t <= 0: return 0.
    if t >= run: return 1.
    if t < e:
        v = t/2-e*math.sin(math.pi*t/e)/(2*math.pi)
    elif t <= run-e:
        v = t-e/2
    else:
        q = run-t
        v = run-e-(q/2-e*math.sin(math.pi*q/e)/(2*math.pi))
    return v/(run-e)


def height(theta):
    q = (theta-math.pi)/TAU
    if q <= 0: return Z0
    if q >= 3: return Z0+3*PITCH
    k = math.floor(q)
    return Z0+PITCH*(k+rise(q-k))


def polar(r, theta, z=None):
    return (CX+r*math.cos(theta), CY+r*math.sin(theta), height(theta) if z is None else z)


def opening(t):
    return any(abs(t-(math.pi+k*TAU)) < ALPHA-1e-10 for k in range(4))


def color_turn(t):
    return COLORS[min(2, max(0, math.floor((t-math.pi)/TAU)))]


class Mesh:
    def __init__(self): self.v, self.f, self.c = [], [], []
    def face(self, vertices, color=BLACK):
        n = len(self.v); self.v.extend(vertices)
        self.f.append(list(range(n, n+len(vertices)))); self.c.append(color)
    def polydata(self):
        pts, cells, colors = vtk.vtkPoints(), vtk.vtkCellArray(), vtk.vtkUnsignedCharArray()
        pts.SetDataTypeToDouble(); colors.SetName('turn_color'); colors.SetNumberOfComponents(3)
        for v in self.v: pts.InsertNextPoint(v)
        for f, c in zip(self.f, self.c):
            cells.InsertNextCell(len(f))
            for i in f: cells.InsertCellPoint(i)
            colors.InsertNextTuple3(*(round(x*255) for x in c))
        p = vtk.vtkPolyData(); p.SetPoints(pts); p.SetPolys(cells); p.GetCellData().SetScalars(colors)
        clean = vtk.vtkCleanPolyData(); clean.SetInputData(p); clean.ToleranceIsAbsoluteOn(); clean.SetAbsoluteTolerance(1e-7); clean.Update()
        tri = vtk.vtkTriangleFilter(); tri.SetInputConnection(clean.GetOutputPort()); tri.Update()
        return tri.GetOutput()


def actor(poly, color, category, name, colored=False):
    mapper = vtk.vtkPolyDataMapper(); mapper.SetInputData(poly)
    mapper.SetScalarModeToUseCellData(); mapper.SetColorModeToDirectScalars(); mapper.SetScalarVisibility(colored)
    a = vtk.vtkActor(); a.SetMapper(mapper)
    p=a.GetProperty(); p.SetColor(color); p.SetAmbient(.35); p.SetDiffuse(.65); p.SetSpecular(.18); p.SetSpecularPower(28)
    if category in ('mark','road-mark'):
        p.SetAmbient(1); p.SetDiffuse(0); p.SetSpecular(0)
    SCENE.append((a, category, name)); return a


def part_actor(shape,color,category,name):
    assert shape.isValid(),name
    points,faces=shape.tessellate(.12); m=Mesh()
    for f in faces: m.face([(points[i].x,points[i].y,points[i].z) for i in f],color)
    return actor(m.polydata(),color,category,name)


def box(x0, x1, y0, y1, z0, z1, color=BLACK, category='garage', name='box'):
    s=vtk.vtkCubeSource(); s.SetBounds(x0,x1,y0,y1,z0,z1); s.Update()
    return actor(s.GetOutput(),color,category,name)


def cylinder(x,y,z0,z1,r,color=BLACK,category='support',name='post'):
    s=vtk.vtkCylinderSource(); s.SetResolution(48); s.SetRadius(r); s.SetHeight(z1-z0)
    s.Update(); t=vtk.vtkTransform(); t.Translate(x,y,(z0+z1)/2); t.RotateX(90)
    f=vtk.vtkTransformPolyDataFilter(); f.SetTransform(t); f.SetInputConnection(s.GetOutputPort()); f.Update()
    return actor(f.GetOutput(),color,category,name)


def text3d(value, origin, dx=(1,0,0), dy=(0,0,1), size=10, color=WHITE, category='decoration', name='text'):
    s=vtk.vtkVectorText(); s.SetText(value); s.Update()
    p=vtk.vtkPolyData(); p.DeepCopy(s.GetOutput()); pts=vtk.vtkPoints()
    origin, dx, dy = np.array(origin), np.array(dx), np.array(dy)
    for i in range(p.GetNumberOfPoints()):
        x,y,_=p.GetPoint(i); pts.InsertNextPoint(origin+size*(x*dx+y*dy))
    p.SetPoints(pts); a=actor(p,color,category,name)
    a.GetProperty().SetAmbient(1); a.GetProperty().SetDiffuse(0); a.GetProperty().SetSpecular(0)
    return a


def road_geometry():
    t0, t1 = math.pi-LANDING, math.pi+3*TAU+LANDING
    ts=list(np.linspace(t0,t1,2301))
    for k in range(4):
        mid=math.pi+k*TAU
        ts.extend([mid,mid-LANDING,mid+LANDING,mid-ALPHA,mid+ALPHA])
        ts.extend(np.linspace(mid-ALPHA,mid+ALPHA,61))
    ts=sorted(set(round(float(t),12) for t in ts))
    m=Mesh(); cut_x=[]
    def emit(v,c,terminal=False):
        v=clip_terminal(v) if terminal else v
        if not v: return
        if terminal: cut_x.extend(p[0] for p in v if abs(p[1]-TERMINAL_Y)<1e-7)
        m.face(v,c)
    for a,b in zip(ts,ts[1:]):
        ia,oa,ib,ob=polar(RI,a),polar(RO,a),polar(RI,b),polar(RO,b)
        iad,oad,ibd,obd=[(x,y,z-THICK) for x,y,z in (ia,oa,ib,ob)]
        c=color_turn((a+b)/2)
        terminal=a>=math.pi+3*TAU-1e-9
        emit([ia,oa,ob,ib],c,terminal); emit([iad,ibd,obd,oad],c,terminal)
        emit([ia,ib,ibd,iad],c,terminal)
        if not opening((a+b)/2): emit([oa,oad,obd,ob],c,terminal)
    for t,reverse in [(ts[0],False),(ts[-1],True)]:
        i,o=polar(RI,t),polar(RO,t); f=[i,(i[0],i[1],i[2]-THICK),(o[0],o[1],o[2]-THICK),o]
        emit(f[::-1] if reverse else f,color_turn(t),reverse)
    xs=sorted(set(round(float(x),9) for x in cut_x)); z=Z0+3*PITCH
    for a,b in zip(xs,xs[1:]):
        m.face([(a,TERMINAL_Y,z),(a,TERMINAL_Y,z-THICK),(b,TERMINAL_Y,z-THICK),(b,TERMINAL_Y,z)],RED)
    # Bridges terminate exactly at the road's outside arc; the top surface is
    # neither flared nor overlapped, and the opening in the wall is also 70 mm.
    bridge_checks=[]
    for k in range(4):
        mid=math.pi+k*TAU; z=Z0+k*PITCH
        arc=[t for t in ts if mid-ALPHA-1e-10 <= t <= mid+ALPHA+1e-10]
        assert max(abs(height(t)-z) for t in arc)<1e-8
        for a,b in zip(arc,arc[1:]):
            ra,rb=polar(RO,a,z),polar(RO,b,z); la,lb=(BRIDGE_X,ra[1],z),(BRIDGE_X,rb[1],z)
            top=[la,lb,rb,ra]; bottom=[(x,y,vz-THICK) for x,y,vz in top]
            m.face(top,GRAY); m.face(bottom[::-1],GRAY)
            m.face([la,(la[0],la[1],z-THICK),(lb[0],lb[1],z-THICK),lb],GRAY)
        for t in [arc[0],arc[-1]]:
            r=polar(RO,t,z); l=(BRIDGE_X,r[1],z)
            m.face([l,r,(r[0],r[1],z-THICK),(l[0],l[1],z-THICK)],GRAY)
        ys=[polar(RO,t)[1] for t in arc]
        bridge_checks.append(dict(floor=k+1,clear_width_mm=max(ys)-min(ys),max_step_mm=max(abs(height(t)-z) for t in arc)))
    return m.polydata(),ts,bridge_checks


def curbs(ts):
    meshes=[Mesh(),Mesh(),Mesh()]
    for a,b in zip(ts,ts[1:]):
        t=(a+b)/2; k=min(2,max(0,math.floor((t-math.pi)/TAU))); c=COLORS[k]
        for low,high in [(RI-2,RI),(RO,RO+2)]:
            if low==RO and opening(t): continue
            v=[polar(low,a),polar(high,a),polar(high,b),polar(low,b)]
            up=[(x,y,z+8) for x,y,z in v]
            faces=[up]+[[v[j],v[(j+1)%4],up[(j+1)%4],up[j]] for j in range(4)]
            for face in faces:
                if a>=math.pi+3*TAU-1e-9: face=clip_terminal(face)
                if face: meshes[k].face(face,c)
    for k,m in enumerate(meshes): actor(m.polydata(),COLORS[k],'curb','curb-'+str(k))
    # End stops terminate the two flat turning bays; they are outside the
    # side-entry openings and never across a through section of the helix.
    for t in (ts[0],):
        da=2/120; m=Mesh(); c=color_turn(t)
        v=[polar(RI-2,t-da),polar(RO+2,t-da),polar(RO+2,t+da),polar(RI-2,t+da)]
        u=[(x,y,z+8) for x,y,z in v]; m.face(u,c)
        for j in range(4): m.face([v[j],v[(j+1)%4],u[(j+1)%4],u[j]],c)
        actor(m.polydata(),c,'curb','end-stop')
    # 4F ends at the same straight front edge as its parking connection.
    inner_x=CX-math.sqrt((RI-2)**2-HALF_W**2); z=Z0+3*PITCH
    box(BRIDGE_X,inner_x,TERMINAL_Y-2,TERMINAL_Y,z,z+8,RED,'curb','end-stop')
    # The bridge rails stay outside y=40..110 all the way to the outer arc.
    for k in range(4):
        z=Z0+k*PITCH; c=COLORS[min(2,max(0,k-1))]
        for ya,yb in [(CY-HALF_W-2,CY-HALF_W),(CY+HALF_W,CY+HALF_W+2)]:
            if k==3 and ya<CY: continue
            m=Mesh()
            ys=np.linspace(ya,yb,9)
            for y0,y1 in zip(ys,ys[1:]):
                x0=CX-math.sqrt(RO**2-(y0-CY)**2); x1=CX-math.sqrt(RO**2-(y1-CY)**2)
                v=[(BRIDGE_X,y0,z),(x0,y0,z),(x1,y1,z),(BRIDGE_X,y1,z)]
                u=[(x,y,z+8) for x,y,z in v]; m.face(u,c)
                for j in range(4): m.face([v[j],v[(j+1)%4],u[(j+1)%4],u[j]],c)
            actor(m.polydata(),c,'curb','bridge-rail-'+str(k))


def parking_and_signs():
    bracket_clearances=[]
    locations=[]
    for i,deg in enumerate((35,95,275)):
        t=math.radians(deg); locations.append((f'B{i+1}',t,CX+169*math.cos(t),CY+169*math.sin(t)))
    locations.append(('C',0.,602.,74.))
    base=mounts.box(-10,625,-92,242,0,1.3)
    for name,t,x,y in locations:
        base=base.fuse(mounts.transformed(mounts.base_pad(),t,(x,y,0)))
    for name,t,x,y in locations:
        for v in (-10.5,10.5):
            p=mounts.V(x-v*math.sin(t),y+v*math.cos(t),-3)
            base=base.cut(mounts.Part.makeCylinder(1.7,5,p))
    part_actor(base.removeSplitter(),BLACK,'base','base')
    for x in (3,612):
        for y in (-77,227): cylinder(x,y,-6,0,8,BLACK,'base','foot-pad')
    for k in range(4):
        z=Z0+k*PITCH; c=BLACK if k==0 else COLORS[k-1]
        deck=mounts.box(0,200,0,230,z-(8 if k==0 else THICK),z)
        for x in (12,188):
            for y in (14,216):
                if k: deck=deck.cut(mounts.Part.makeCylinder(3.25,9,mounts.V(x,y,z-8)))
                else: deck=deck.fuse(mounts.Part.makeCylinder(3,3,mounts.V(x,y,z)))
        part_actor(deck,BLACK,'garage','deck-'+str(k))
        box(0,200,-.6,0,z-3,z,c,'decoration','trim-'+str(k))
        bounds=[20,118,180] if k<2 else [20,73.333,126.667,180]
        for j,(a,b) in enumerate(zip(bounds,bounds[1:])):
            for x in [a+3,b-3]: box(x-.6,x+.6,124,214,z+.025,z+.07,WHITE,'mark','bay-line')
            box(a+3,b-3,213,214,z+.025,z+.07,WHITE,'mark','bay-back')
            text3d(str((k+1)*100+j+1),(a+7,113,z+.08),(1,0,0),(0,1,0),5,WHITE,'mark','bay-number')
        if k<2:
            box(22,49,126,211,z+.005,z+.022,BLUE,'mark','accessible-band')
            text3d('P',(26,113,z+.09),(1,0,0),(0,1,0),7,WHITE,'mark','accessible-P')
        for y in np.arange(127,211,9):
            for a,b in [(3,16),(184,197)]:
                m=Mesh(); m.face([(a,y,z+.08),(b,y+4,z+.08),(b,y+5.3,z+.08),(a,y+1.3,z+.08)],CYAN)
                actor(m.polydata(),CYAN,'mark','hatching')
        for y in range(37,103,9): box(20,39,y,y+3,z+.03,z+.08,WHITE,'mark','zebra')
        m=Mesh(); m.face([(73,72,z+.1),(138,72,z+.1),(138,67,z+.1),(152,75,z+.1),(138,83,z+.1),(138,78,z+.1),(73,78,z+.1)],WHITE)
        actor(m.polydata(),WHITE,'mark','aisle-arrow')
        if k:
            box(157,193,-2,-.7,z-17,z-1,BLACK,'decoration','floor-label')
            text3d(f'{k+1}F',(161,-2.05,z-14),size=10,category='decoration',name='floor-text')
        else: text3d('1F',(158,-.7,1),size=5,category='decoration',name='floor-text')
    box(0,200,229,233,1,232,BLACK,'garage','back-wall')
    for x in (12,188):
        for y in (14,216):
            for k in range(4):
                s=mounts.garage_segment(Z0+k*PITCH,k==3); s.translate(mounts.V(x,y,0))
                part_actor(s,BLACK,'support','garage-column')
    for name,t,x,y in locations:
        angle=t
        while angle<math.pi: angle+=TAU
        levels=[height(angle+k*TAU) for k in range(3)] if name!='C' else []
        post=mounts.upright(levels,243 if name=='C' else 205)
        part_actor(mounts.transformed(post,t,(x,y,0)),BLACK,'support',name+'-upright')
        for p in mounts.foot_hardware(): part_actor(mounts.transformed(p['shape'],t,(x,y,0)),p['color'],'support',name+'-'+p['name'])
        if name=='C': continue
        parts=mounts.station(angle,height)
        mounts.interference_checks(parts,post,height(angle))
        for k in range(3):
            h=height(angle+k*TAU)
            for p in parts:
                if p['role']=='road': continue
                s=mounts.transformed(p['shape'],t,(x,y,h))
                part_actor(s,p['color'],'support',name+'-'+p['name']+str(k))
                if k and p['role'] in ('arm','road-bolt','road-washer'):
                    vertices,_=p['shape'].tessellate(.12)
                    for v in vertices:
                        radius=math.hypot(169+v.x,v.y)
                        if RI<=radius<=RO:
                            lower=height(angle+(k-1)*TAU+math.atan2(v.y,169+v.x))
                            bracket_clearances.append(h+v.z-lower)
    box(0,196,226,231,263,319,BLACK,'sign','billboard')
    for x,c in [(28,CYAN),(151,RED)]: box(x,x+15,225,231,230,265,c,'sign','billboard-post')
    text3d('Lovely Cars',(15,225.8,293),size=17,category='sign',name='billboard-text')
    text3d("I've Driven",(15,225.8,270),size=17,category='sign',name='billboard-text')
    box(588,619,65,69,107,241,BLACK,'sign','side-sign-frame')
    box(590,617,64.6,65,109,239,BLUE,'sign','side-sign-blue')
    for x,value in [(593,'HORSEPOWER LEFT,'),(606,'BRAINPOWER RIGHT')]:
        text3d(value,(x,64.3,230),dx=(0,0,-1),dy=(1,0,0),size=7,color=WHITE,category='sign',name='side-sign-text')
    return bracket_clearances


def arrows():
    for k in range(3):
        for u in (.24,.72):
            t=math.pi+TAU*(k+u)
            shape=[(-1.3,-12),(1.3,-12),(1.3,3),(5,3),(0,13),(-5,3),(-1.3,3)]
            m=Mesh(); m.face([polar(120+dr,t+along/120,height(t+along/120)+.1) for dr,along in shape],WHITE)
            actor(m.polydata(),WHITE,'road-mark','up-arrow')


def render(filename, mode, road_actor, road_poly):
    renderer=vtk.vtkRenderer(); renderer.SetBackground(.974,.974,.966); renderer.SetUseFXAA(True)
    selected=[]
    for a,category,name in SCENE:
        keep=mode=='overall' or (mode=='road' and category in ('road','curb','road-mark'))
        if mode=='plan':
            keep=category in ('road','curb','road-mark') or name in ('deck-0','base')
            if name=='end-stop': keep=False
            if name=='base': a.GetProperty().SetColor(.87,.89,.90)
            if name=='deck-0': a.GetProperty().SetColor(.31,.34,.37)
        if keep: renderer.AddActor(a); selected.append(a)
    road_actor.GetMapper().SetScalarVisibility(mode=='road')
    light=vtk.vtkLight(); light.SetLightTypeToSceneLight(); light.SetPosition(-250,-500,900); light.SetFocalPoint(280,70,90); light.SetIntensity(.9); renderer.AddLight(light)
    fill=vtk.vtkLight(); fill.SetLightTypeToSceneLight(); fill.SetPosition(850,100,550); fill.SetFocalPoint(280,70,90); fill.SetIntensity(.55); renderer.AddLight(fill)
    w=vtk.vtkRenderWindow(); w.SetOffScreenRendering(1); w.SetSize(1800,1350); w.SetMultiSamples(8); w.AddRenderer(renderer)
    cam=renderer.GetActiveCamera(); cam.ParallelProjectionOn()
    if mode=='overall':
        cam.SetPosition(-530,-1160,810); cam.SetFocalPoint(300,75,132); cam.SetViewUp(0,0,1)
    elif mode=='road':
        cam.SetPosition(-320,-1130,740); cam.SetFocalPoint(397,75,100); cam.SetViewUp(0,0,1)
    else:
        cam.SetPosition(310,75,1500); cam.SetFocalPoint(310,75,0); cam.SetViewUp(0,1,0)
    # Fit the actual projected vertices into the drawing area, keeping the
    # title and footer clear rather than fitting a loose world-space sphere.
    toward=np.array(cam.GetPosition())-np.array(cam.GetFocalPoint()); toward/=np.linalg.norm(toward)
    right=np.cross(np.array(cam.GetViewUp()),toward); right/=np.linalg.norm(right)
    up=np.cross(toward,right)
    cloud=np.concatenate([vtk_to_numpy(a.GetMapper().GetInput().GetPoints().GetData()) for a in selected])
    projected=cloud@np.stack([right,up,toward],axis=1); lo=projected.min(axis=0); hi=projected.max(axis=0)
    mid=(lo+hi)/2; focal=mid[0]*right+mid[1]*up+mid[2]*toward
    cam.SetFocalPoint(*focal); cam.SetPosition(*(focal+1500*toward))
    cam.SetParallelScale(max((hi[1]-lo[1])*1350/(2*1000),(hi[0]-lo[0])*1350/(2*1640)))
    renderer.ResetCameraClippingRange(); w.Render()
    c=vtk.vtkWindowToImageFilter(); c.SetInput(w); c.SetInputBufferTypeToRGB(); c.ReadFrontBufferOff(); c.Update()
    data=vtk_to_numpy(c.GetOutput().GetPointData().GetScalars()).reshape(1350,1800,3)
    image=Image.fromarray(np.flipud(data).copy()); draw=ImageDraw.Draw(image)
    font='/System/Library/Fonts/STHeiti Medium.ttc'
    f40=ImageFont.truetype(font,40); f26=ImageFont.truetype(font,26); f23=ImageFont.truetype(font,23)
    draw.rectangle((0,0,1800,140),fill=(248,248,246)); draw.rectangle((0,1245,1800,1350),fill=(248,248,246))
    titles={'overall':'四层停车场｜等宽单车道几何重建','road':'同一条连续坡道｜移去停车楼，仅看真实道路','plan':'俯视校核｜入口与整圈道路均为 70 mm 净宽'}
    subtitles={'overall':'模型直接渲染 · 坡道不分叉 · 停车层只从外侧接入','road':'同一份几何：浅蓝 1F→2F / 深蓝 2F→3F / 红 3F→4F','plan':'车道边界的平面投影；省略端部挡墙，层间高差见坡道图'}
    draw.text((65,32),titles[mode],font=f40,fill=(30,45,55)); draw.text((65,91),subtitles[mode],font=f26,fill=(81,100,111))
    draw.text((65,1270),'净路宽 70 mm   ·   内半径 85 mm   ·   外半径 155 mm   ·   三圈跨四层',font=f26,fill=(30,45,55))
    draw.text((65,1312),'几何及安装方案预览；尺寸配合、承载、实车转向及打印拆件仍待验证。',font=f23,fill=(81,100,111))
    def screen(point):
        renderer.SetWorldPoint(*point,1); renderer.WorldToDisplay(); x,y,_=renderer.GetDisplayPoint(); return np.array([x,1350-y])
    def dimension(a,b,label,offset):
        p,q=screen(a),screen(b); color=(169,48,54)
        draw.line([tuple(p),tuple(q)],fill=color,width=3)
        unit=(q-p)/np.linalg.norm(q-p); perp=np.array([-unit[1],unit[0]])
        for end,direction in [(p,unit),(q,-unit)]:
            for sign in (-1,1): draw.line([tuple(end),tuple(end+direction*14+sign*perp*7)],fill=color,width=3)
        mid=(p+q)/2+np.array(offset); bounds=draw.textbbox(tuple(mid),label,font=f26)
        draw.rectangle((bounds[0]-9,bounds[1]-6,bounds[2]+9,bounds[3]+6),fill=(248,248,246))
        draw.text(tuple(mid),label,font=f26,fill=color)
    if mode=='plan':
        dimension((225,40,8),(225,110,8),'入口 70 mm',(-165,-10))
        dimension((CX+RI,CY,100),(CX+RO,CY,100),'路宽 70 mm',(-66,-53))
    if mode=='road':
        for k in range(4):
            p=screen((200,75,Z0+k*PITCH)); draw.text(tuple(p+[-78,-17]),f'{k+1}F',font=f26,fill=(30,45,55))
    image.save(ROOT/filename)
    w.Finalize()


def main():
    road_poly,ts,bridges=road_geometry()
    render_road=road_poly
    normals=vtk.vtkPolyDataNormals(); normals.SetInputData(road_poly); normals.ConsistencyOn(); normals.AutoOrientNormalsOn(); normals.SplittingOff(); normals.Update()
    road_poly=normals.GetOutput()
    connected=vtk.vtkPolyDataConnectivityFilter(); connected.SetInputData(road_poly); connected.SetExtractionModeToAllRegions(); connected.Update()
    assert connected.GetNumberOfExtractedRegions()==1
    edges=vtk.vtkFeatureEdges(); edges.SetInputData(road_poly); edges.BoundaryEdgesOn(); edges.NonManifoldEdgesOn(); edges.FeatureEdgesOff(); edges.ManifoldEdgesOff(); edges.Update()
    bad_edges=edges.GetOutput().GetNumberOfCells()
    assert bad_edges==0, f'Road/bridge mesh has {bad_edges} open or non-manifold edges'
    widths=[np.linalg.norm(np.array(polar(RO,t))-np.array(polar(RI,t))) for t in ts]
    assert max(abs(v-70) for v in widths)<1e-8
    assert all(abs(b['clear_width_mm']-70)<1e-7 and b['max_step_mm']<1e-8 for b in bridges)
    report=dict(units='mm',road_width_min=min(widths),road_width_max=max(widths),radii=[RI,RO],turns=3,floors=4,pitch=PITCH,slab_thickness=THICK,slab_to_slab_clearance=PITCH-THICK,main_road_branches=0,side_parking_connections=4,bridges=bridges,open_or_nonmanifold_mesh_edges=bad_edges,landing_half_angle_degrees=25,maximum_centerline_grade=PITCH/(120*math.radians(295)),maximum_inner_edge_grade=PITCH/(RI*math.radians(295)),scope='Geometry only; not a manufacturing or vehicle-steering validation')
    report['connected_road_mesh_components']=connected.GetNumberOfExtractedRegions()
    points=vtk_to_numpy(road_poly.GetPoints().GetData())
    terminal=points[(points[:,2]>=Z0+3*PITCH-THICK-1e-7)&(points[:,0]<CX)]
    assert terminal[:,1].min()>=TERMINAL_Y-1e-7
    report['fourth_floor_tail_removed']=True
    report['fourth_floor_terminal_y_mm']=TERMINAL_Y
    writer=vtk.vtkXMLPolyDataWriter(); writer.SetFileName(str(ROOT/'constant-width-road.vtp')); writer.SetInputData(road_poly); writer.Write()
    road_actor=actor(render_road,BLACK,'road','main-road')
    curbs(ts); gaps=parking_and_signs(); arrows()
    assert min(gaps)>45
    report['minimum_clearance_under_brackets_mm']=min(gaps)
    cloud=np.concatenate([vtk_to_numpy(a.GetMapper().GetInput().GetPoints().GetData()) for a,_,_ in SCENE])
    report['overall_envelope_mm']=(cloud.max(axis=0)-cloud.min(axis=0)).tolist()
    report['outer_post_diameter_mm']=14
    report['support_mounting']='original garage column solids; 6.6 mm bearing-tab arms; height-set feet; underside M3 screws'
    report['reused_external_standard_segments']=9
    report['reused_external_top_caps']=4
    (ROOT/'geometry-checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    for filename,mode in [('09-geometry-overall.png','overall'),('10-geometry-road-only.png','road'),('11-geometry-width-plan.png','plan')]:
        render(filename,mode,road_actor,road_poly); print('Rendered',filename,flush=True)
    (ROOT/'render-smoke.png').unlink(missing_ok=True)
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__': main()
