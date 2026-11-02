"""Proposed mounting parts, in mm; real BRep holes, seats and split collars.

The ramp layout is fixed; mounting clearances are a design study pending fit tests.
Local station axes: X radial outward, Y tangent, Z vertical; road top at (0,0)=0.
"""
import math
import sys
sys.dont_write_bytecode=True
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as App
import Part

V=App.Vector
BLACK=(.095,.11,.13)
STEEL=(.65,.69,.72)
GOLD=(.78,.56,.19)
POST_R=7.
COLLAR_R=11.
BORE_R=7.2
ARM_DEPTH=5.
CLAMP_BOTTOM=-16.6
CLAMP_TOP=-6.6


def box(x0,x1,y0,y1,z0,z1): return Part.makeBox(x1-x0,y1-y0,z1-z0,V(x0,y0,z0))
def cyl(r,z0,z1,x=0,y=0): return Part.makeCylinder(r,z1-z0,V(x,y,z0))


def hex_prism(af,length,origin,axis):
    n=V(axis); n.normalize(); a=V(0,0,1) if abs(n.z)<.9 else V(1,0,0)
    u=n.cross(a); u.normalize(); v=n.cross(u); r=af/math.sqrt(3)
    points=[V(origin)+r*(math.cos(k*math.pi/3)*u+math.sin(k*math.pi/3)*v) for k in range(6)]
    return Part.Face(Part.makePolygon(points+[points[0]])).extrude(n*length)


def bolt(origin,axis,length):
    """Under-head origin; axis points along the shank into the joint."""
    p,n=V(origin),V(axis); n.normalize()
    shank=Part.makeCylinder(1.5,length,p,n)
    head=Part.makeCylinder(2.75,3,p,-n)
    recess=hex_prism(2.5,1.6,p-n*3,n)
    return shank.fuse(head).cut(recess).removeSplitter()


def washer(origin,axis):
    n=V(axis); n.normalize(); p=V(origin)
    return Part.makeCylinder(3.5,.5,p,n).cut(Part.makeCylinder(1.6,.5,p,n))


def nut(origin,axis):
    n=V(axis); n.normalize(); p=V(origin)
    return hex_prism(5.5,2.4,p,n).cut(Part.makeCylinder(1.5,2.4,p,n))


def record(name,shape,role,color=BLACK,explode=(0,0,0)):
    assert shape.isValid() and len(shape.Solids)==1,(name,len(shape.Solids))
    return dict(name=name,shape=shape,role=role,color=color,explode=explode)


def top_z(theta,r,v,height): return height(theta+math.atan2(v,r))-height(theta)


def arm_loft(theta,height):
    profiles=[]
    for r in [85,95,110,125,140,145,155,161.8]:
        u=r-169; a=top_z(theta,r,-8,height)-6.6; b=top_z(theta,r,8,height)-6.6
        pts=[V(u,-8,a),V(u,8,b),V(u,8,b-5),V(u,-8,a-5)]
        profiles.append(Part.makePolygon(pts+[pts[0]]))
    return Part.makeLoft(profiles,True,False)


def road_patch(theta,height):
    wires=[]; da=math.radians(12)
    for r in [85,95,110,125,140,145,155]:
        a,b=height(theta-da)-height(theta),height(theta+da)-height(theta)
        x=r*math.cos(da)-169; v=r*math.sin(da)
        pts=[V(x,-v,a),V(x,v,b),V(x,v,b-6.6),V(x,-v,a-6.6)]
        wires.append(Part.makePolygon(pts+[pts[0]]))
    return Part.makeLoft(wires,True,False)


def station(theta,height):
    ring=cyl(COLLAR_R,CLAMP_BOTTOM,CLAMP_TOP).cut(cyl(BORE_R,CLAMP_BOTTOM-1,CLAMP_TOP+1))
    inner=ring.common(box(-20,-.3,-20,20,-20,0)); cap=ring.common(box(.3,20,-20,20,-20,0))
    for v0,v1 in [(10,18),(-18,-10)]:
        inner=inner.fuse(box(-6,-.3,v0,v1,CLAMP_BOTTOM,CLAMP_TOP))
        cap=cap.fuse(box(.3,6,v0,v1,CLAMP_BOTTOM,CLAMP_TOP))
    inner=inner.fuse(arm_loft(theta,height)).cut(cyl(BORE_R,-30,2))
    for v in [-14,14]:
        hole=Part.makeCylinder(1.7,28,V(-14,v,-11.6),V(1,0,0))
        inner=inner.cut(hole).cut(hex_prism(5.8,2.8,V(-6,v,-11.6),V(1,0,0)))
        cap=cap.cut(hole)
    road=road_patch(theta,height)
    hardware=[]
    for i,r in enumerate([110,145]):
        derivative=(height(theta+1e-5)-height(theta-1e-5))/(2e-5)
        slope=derivative/r; n=V(0,-slope,1); n.normalize(); p=V(r-169,0,-6.6)
        inner=inner.cut(Part.makeCylinder(1.7,18,p-n*12,n))
        # Manufacturer RX-M3Sx4.0: pilot Ø4, blind depth >=5; insert length 4.
        road=road.cut(Part.makeCylinder(2.,5.,p,n))
        insert=Part.makeCylinder(2.3,4,p,n).cut(Part.makeCylinder(1.5,4,p,n))
        beam_normal_depth=5/math.sqrt(1+slope*slope)
        under=p-n*(beam_normal_depth+.5)
        hardware.append(record(f'road_insert_{i+1}',insert,'insert',GOLD,(0,0,18)))
        hardware.append(record(f'road_washer_{i+1}',washer(under,n),'road-washer',STEEL,(0,0,-20)))
        hardware.append(record(f'road_bolt_{i+1}',bolt(under,n,10),'road-bolt',STEEL,(0,0,-20)))
    parts=[record('arm_inner_clamp',inner.removeSplitter(),'arm'),record('outer_clamp_cap',cap.removeSplitter(),'cap',BLACK,(28,0,0)),record('road_patch',road,'road',(.18,.60,.78),(0,0,28))]
    for i,v in enumerate([-14,14]):
        parts.append(record(f'clamp_bolt_{i+1}',bolt(V(6.5,v,-11.6),V(-1,0,0),16),'clamp-bolt',STEEL,(54,0,0)))
        parts.append(record(f'clamp_washer_{i+1}',washer(V(6,v,-11.6),V(1,0,0)),'clamp-washer',STEEL,(28,0,0)))
        parts.append(record(f'clamp_nut_{i+1}',nut(V(-6,v,-11.6),V(1,0,0)),'clamp-nut',STEEL,(-9,0,0)))
    return parts+hardware


def upright(road_heights,top=205):
    s=cyl(7,1.3,top).fuse(cyl(14,1.3,4.3))
    for z in road_heights:
        seat=z+CLAMP_BOTTOM
        s=s.fuse(Part.makeCone(7,9,2,V(0,0,seat-2)))
    for v in [-10.5,10.5]: s=s.cut(Part.makeCylinder(1.7,6,V(0,v,0)))
    return s.removeSplitter()


def base_pad():
    s=cyl(15,-2,1.3)
    for v in [-10.5,10.5]: s=s.cut(Part.makeCylinder(1.7,5,V(0,v,-3)))
    return s


def foot_hardware():
    out=[]
    for i,v in enumerate([-10.5,10.5]):
        out.append(record(f'foot_bolt_{i+1}',bolt(V(0,v,4.8),V(0,0,-1),10),'foot-bolt',STEEL,(0,0,16)))
        out.append(record(f'foot_top_washer_{i+1}',washer(V(0,v,4.3),V(0,0,1)),'foot-washer',STEEL,(0,0,16)))
        out.append(record(f'foot_bottom_washer_{i+1}',washer(V(0,v,-2.5),V(0,0,1)),'foot-washer',STEEL,(0,0,-8)))
        out.append(record(f'foot_nut_{i+1}',nut(V(0,v,-4.9),V(0,0,1)),'foot-nut',STEEL,(0,0,-8)))
    return out


def garage_segment(z,top=False):
    h=35 if top else 56.4
    s=cyl(7,z,z+h).cut(cyl(3.25,z-1,z+3.3))
    if not top:
        s=s.fuse(cyl(10,z+h-4,z+h)).fuse(Part.makeCone(7,10,3,V(0,0,z+h-7))).fuse(cyl(3,z+h,z+h+9.6))
    return s.removeSplitter()


def garage_floor(z): return box(-24,24,-23,23,z-6.6,z).cut(cyl(3.25,z-8,z+1))


def transformed(shape,theta,origin):
    s=shape.copy(); s.rotate(V(0,0,0),V(0,0,1),math.degrees(theta)); s.translate(V(origin)); return s


def interference_checks(parts,post,road_height):
    arm=next(p['shape'] for p in parts if p['role']=='arm')
    cap=next(p['shape'] for p in parts if p['role']=='cap')
    localpost=post.copy(); localpost.translate(V(0,0,-road_height))
    values=dict(arm_post_overlap_mm3=arm.common(localpost).Volume,cap_post_overlap_mm3=cap.common(localpost).Volume,clamp_halves_overlap_mm3=arm.common(cap).Volume)
    assert max(values.values())<1e-5,values
    return values
