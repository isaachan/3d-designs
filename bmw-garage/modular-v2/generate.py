"""Modular garage engineering draft. Run with ../.venv/bin/python generate.py.
All dimensions in mm. Coordinate: X right, Y rearward, Z up; front is -Y.
No geometry is read from or written back to the v1 project.
"""
from pathlib import Path
import sys, json, zipfile, xml.etree.ElementTree as E
import numpy as np
import trimesh as tm
from shapely.geometry import box, Polygon
from shapely.ops import unary_union
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from convert_to_bmw import text, roundel, extrude, put_mesh, tag, xml, CORE, PROD
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent
OUT=HERE/'generated'
GAP=.30  # each side, NOT total diametral clearance
COLORS={1:'#16191D',2:'#F4D52D',3:'#979CA3',4:'#FFFFFF',5:'#0066CC'}
NAMES=['Road and parking - UNIVERSAL','Showroom - UNIVERSAL','Glass - BMW KIT','Signs - BMW KIT','Wheel stops - UNIVERSAL','Office - BMW KIT']
items=[]

def block(x0,x1,y0,y1,z0,z1):
    m=tm.creation.box((x1-x0,y1-y0,z1-z0)); m.apply_translation(((x0+x1)/2,(y0+y1)/2,(z0+z1)/2)); return m

def union(ms): return tm.boolean.union(ms,engine='manifold') if len(ms)>1 else ms[0].copy()
def diff(m,ms): return tm.boolean.difference([m,*ms],engine='manifold') if ms else m.copy()
def move(m,d):
    m=m.copy(); m.apply_translation(d); return m

def transform(m,matrix):
    m=m.copy(); m.apply_transform(matrix); return m

IDENTITY=np.eye(4)
# Sign print XY represents assembly XZ; printed depth points rearward (+Y).
SIGN=np.array([[1,0,0,0],[0,0,1,0],[0,1,0,0],[0,0,0,1]],float)
# Reflection is intentional; trimesh flips winding for a negative determinant.
PANEL=np.array([[0,0,1,0],[1,0,0,0],[0,1,0,0],[0,0,0,1]],float)

def add(name,plate,parts,print_matrix=None):
    # parts are assembly coordinates. print_matrix maps assembly to print coordinates.
    items.append(dict(name=name,plate=plate,parts=parts,print_matrix=IDENTITY if print_matrix is None else print_matrix))

def inlaid(base,regions,z,depth=.4):
    inserts={c:extrude(g.simplify(1e-5,preserve_topology=True),z,depth) for c,g in regions.items() if not g.is_empty}
    assert base.is_volume, ('invalid base',base.is_watertight,base.volume)
    for c,m in inserts.items():
        assert m.is_volume, ('invalid inlay',c,m.is_watertight,m.volume)
    backing=diff(base,list(inserts.values()))
    return backing,inserts

def rail(cx,z,top=False):
    # Open U-channel with 3 mm flared entry and closed rear stop.
    half=1+GAP
    solid=block(cx-half-2,cx+half+2,20,101,z,z+3)
    mouth=Polygon([(cx-half-.8,19),(cx+half+.8,19),(cx+half,23),(cx+half,99.3),(cx-half,99.3),(cx-half,23)])
    return diff(solid,[extrude(mouth,z-.1,3.2)])

def peg(cx,cz,y0):
    # 8 x 4 mm rectangular peg, 5 mm long, last 1 mm tapered.
    p=Polygon([(cx-4,y0),(cx+4,y0),(cx+4,y0+4),(cx+3.3,y0+5),(cx-3.3,y0+5),(cx-4,y0+4)])
    return extrude(p,cz-2,4)

def make_sign(name,w,h,center,zbottom,yfront,spacing,plate,main_text):
    # Print face-down: colored layers are first .4 mm, pegs grow upwards.
    base=block(-w/2,w/2,0,h,0,2.4)
    r=min(h*.40,8)
    art={c:[] for c in [1,4,5]}
    for c,g in roundel(w/2-r-3,h/2,r).items(): art[c].append(g)
    art[4].append(text(main_text,-w/2+5,h*.31,w-2*r-15,h*.34))
    regions={c:unary_union(gs) for c,gs in art.items() if gs and c!=5}
    backing,ins=inlaid(base,regions,0)
    # Local pegs point along print Z.
    pegs=[]
    for x in [-spacing/2,spacing/2]:
        a=peg(x,4,2.4)
        pegs.append(transform(a,np.linalg.inv(SIGN)))
    backing=union([backing,*pegs])
    mat=SIGN.copy(); mat[:3,3]=[center,yfront,zbottom]
    parts={5:transform(backing,mat),**{c:transform(m,mat) for c,m in ins.items()}}
    add(name,plate,parts,np.linalg.inv(mat))


def build():
    # Plate 1: brand-neutral road, five parking places, checker showroom floor.
    floor=block(-110,110,-110,110,0,4)
    guides=[rail(x,4) for x in [-30,45]]
    # Office tray side rails: 0.3 mm side and vertical clearance.
    for x0,x1 in [(47.5,49.7),(98.3,100.5)]:
        guides.append(block(x0,x1,25,94,4,8))
    guides += [block(47.5,51.2,25,94,6.6,8),block(96.8,100.5,25,94,6.6,8),block(49.7,98.3,91.3,94,4,8)]
    floor=union([floor,*guides])
    # Receiver pockets for structural shell locating tabs (not brand interfaces).
    locators=[(-106,35),(-106,94),(106,35),(106,94)]
    floor=diff(floor,[block(x-1.5,x+1.5,y-4.3,y+4.3,1.7,4.1) for x,y in locators])
    markings=[box(-102,-105,102,-103.6),box(-102,-32,102,-30.6),box(-104,15,104,16.4)]
    for x in np.linspace(-102,102,6): markings.append(box(x,-105,x+1.4,-30.6))
    for x in range(-98,104,22): markings.append(box(x,-9,x+12,-7.6))
    for ix in range(15):
        for iy in range(8):
            if (ix+iy)%2==0: markings.append(box(-104+10*ix,22+10*iy,-94+10*ix,32+10*iy))
    # Tiny neutral grout avoids non-manifold point contacts between checker tiles.
    white=unary_union([g.buffer(-.02,join_style=2) for g in markings])
    for guide in guides:
        b=guide.bounds; white=white.difference(box(b[0,0]-.2,b[0,1]-.2,b[1,0]+.2,b[1,1]+.2))
    backing,ins=inlaid(floor,{4:white},3.6)
    add('Universal road + receiver rails',1,{1:backing,**ins})
    # Plate 2: roof and walls print upside down. Open front, no fixed dividers.
    shell=[block(-108,108,20,108,84,92),block(-108,-104,20,108,4,84),block(104,108,20,108,4,84),block(-104,104,104,108,4,84)]
    shell += [rail(x,81,True) for x in [-30,45]]
    # Low socket towers ABOVE opening ensure fascia cannot obstruct glass removal.
    for x in [-92,92]: shell.append(block(x-7,x+7,20,29,84,92))
    for x in [-16,16]: shell.append(block(x-7,x+7,99.5,104,39,48))
    for x,y in locators: shell.append(block(x-1.2,x+1.2,y-4,y+4,2,4.1))
    shell=union(shell)
    sockets=[]
    for x in [-92,92]: sockets.append(block(x-4-GAP,x+4+GAP,19.9,25.7,85.7,90.3))
    for x in [-16,16]: sockets.append(block(x-4-GAP,x+4+GAP,99.4,105.2,40.7,45.3))
    # Open rear cable notch, no claim of compatibility with the v1 LED kit.
    sockets.append(block(88,96,103.9,108.1,78,84.1))
    shell=diff(shell,sockets)
    invert=np.diag([1,-1,-1,1]); invert[2,3]=92
    add('Universal showroom shell',2,{3:shell},invert)
    # Plate 3: identical keyed envelope, independent artwork. Print on plain face.
    for index,cx in enumerate([-30,45]):
        p=box(0,0,77,79.3)
        plain=extrude(p,0,2)
        # Integral grasping tongue at the leading edge, away from upper/lower rails.
        tongue=extrude(box(-4,8,2,20),0,2)
        plain=union([plain,tongue])
        regions=roundel(39,42,23)
        regions={c:g for c,g in regions.items() if c!=4}
        backing,ins=inlaid(plain,regions,1.6)
        mat=PANEL.copy(); mat[:3,3]=[cx-1,22,4.35]
        parts={4:transform(backing,mat),**{c:transform(m,mat) for c,m in ins.items()}}
        add(f'BMW slide-out partition {index+1}',3,parts,np.linalg.inv(mat))
    # Plate 4: paired plug-in fascia and interior sign.
    make_sign('BMW front fascia',200,20,0,84,17.6,184,4,'BMW GARAGE')
    make_sign('BMW interior sign',54,28,0,39,97.1,32,4,'BMW')
    # Plate 5: five neutral yellow stops. Kept loose; glue if desired.
    for i,x in enumerate([-81.6,-40.8,0,40.8,81.6]):
        stop=block(x-12,x+12,-100,-96,4,7)
        stripes=union([block(x+a,x+a+2,-100,-96,6.6,7) for a in [-8,-2,4]])
        add(f'Universal wheel stop {i+1}',5,{2:diff(stop,[stripes]),1:stripes})
    # Plate 6: removable branded office cassette, no support needed in nominal orientation.
    tray=union([block(50,98,26,91,4.3,6.3),block(68,80,21,27,4.3,6.3)])
    desk=union([block(53,95,68,85,6.3,23),block(52,96,66,87,23,25)])
    stools=[]
    for x in [61,87]:
        s=tm.creation.cylinder(radius=4.5,height=9,sections=48); s.apply_translation((x,48,10.8)); stools.append(s)
    office=union([tray,desk,*stools])
    # BMW inlay on the desk's upper face; fascia/decor can change per brand.
    logo=roundel(74,76,7)
    regions={c:g for c,g in logo.items() if c!=5}
    backing,ins=inlaid(office,regions,24.6)
    add('BMW office slide-out cassette',6,{5:backing,**ins})


def normalized(parts,matrix):
    parts={c:transform(m,matrix) for c,m in parts.items()}
    b=tm.util.concatenate(list(parts.values())).bounds
    shift=[-(b[0,0]+b[1,0])/2,-(b[0,1]+b[1,1])/2,-b[0,2]]
    return {c:move(m,shift) for c,m in parts.items()}

def project(path,entries,template=True):
    """Bambu-compatible nested components with per-part filament assignments."""
    root=E.Element(tag('model'),{'unit':'millimeter','{http://www.w3.org/XML/1998/namespace}lang':'en-US'})
    E.SubElement(root,tag('metadata'),{'name':'Application'}).text='BambuStudio-02.08.02.61'
    E.SubElement(root,tag('metadata'),{'name':'BambuStudio:3mfVersion'}).text='1'
    E.SubElement(root,tag('metadata'),{'name':'Title'}).text=path.stem+' / engineering draft - not print tested'
    res=E.SubElement(root,tag('resources')); build=E.SubElement(root,tag('build')); cfg=E.Element('config')
    counter=1; plates={}
    for name,parts,plate,offset in entries:
        pids=[]
        for color,m in parts.items():
            oid=counter; counter+=1
            obj=E.SubElement(res,tag('object'),{'id':str(oid),'type':'model','name':f'{name} - filament {color}'})
            put_mesh(obj,m); pids.append((oid,color,m))
        oid=counter; counter+=1
        obj=E.SubElement(res,tag('object'),{'id':str(oid),'type':'model','name':name}); comps=E.SubElement(obj,tag('components'))
        conf=E.SubElement(cfg,'object',{'id':str(oid)})
        E.SubElement(conf,'metadata',{'key':'name','value':name}); E.SubElement(conf,'metadata',{'key':'extruder','value':str(pids[0][1])})
        for pid,color,m in pids:
            E.SubElement(comps,tag('component'),{'objectid':str(pid)})
            part=E.SubElement(conf,'part',{'id':str(pid),'subtype':'normal_part'})
            E.SubElement(part,'metadata',{'key':'name','value':f'{name} / {color}'})
            E.SubElement(part,'metadata',{'key':'extruder','value':str(color)})
            E.SubElement(part,'mesh_stat',{'face_count':str(len(m.faces)),'edges_fixed':'0','degenerate_facets':'0','facets_removed':'0','facets_reversed':'0','backwards_edges':'0'})
        E.SubElement(build,tag('item'),{'objectid':str(oid),'transform':'1 0 0 0 1 0 0 0 1 '+' '.join(map(str,offset)),'printable':'1'})
        plates.setdefault(plate,[]).append(oid)
    for plate,ids in plates.items():
        p=E.SubElement(cfg,'plate')
        for k,v in [('plater_id',str(plate)),('plater_name','Fit coupons' if path.stem=='Fit-coupons' else NAMES[plate-1].replace('BMW','TEMPLATE') if 'Template' in path.stem else NAMES[plate-1] if plate<=6 else 'Fit coupons'),('locked','false')]: E.SubElement(p,'metadata',{'key':k,'value':v})
        for oid in ids:
            inst=E.SubElement(p,'model_instance')
            for k,v in [('object_id',str(oid)),('instance_id','0'),('identify_id',str(oid))]: E.SubElement(inst,'metadata',{'key':k,'value':v})
    files={'3D/3dmodel.model':xml(root),'Metadata/model_settings.config':xml(cfg)}
    if template:
        with zipfile.ZipFile(HERE.parent/'Garage_BMW.3mf') as z: settings=json.loads(z.read('Metadata/project_settings.config'))
        settings['filament_colour']=list(COLORS.values()); settings['filament_multi_colour']=list(COLORS.values())
        files['Metadata/project_settings.config']=json.dumps(settings,indent=2).encode()
    files['_rels/.rels']=b'<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>'
    files['[Content_Types].xml']=b'<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/><Default Extension="config" ContentType="application/octet-stream"/></Types>'
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        for n,data in files.items(): z.writestr(n,data)


def coupons():
    entries=[]; results=[]
    for i,g in enumerate([.20,.30,.40]):
        # Female rail printed like the real floor, male printed flat like the panel.
        fem=diff(block(0,20,0,28,0,6),[block(9-g,11+g,-.1,25,3,6.1)])
        male=block(0,20,0,12,0,2)
        # Socket coupon printed in roof-down orientation; peg printed face-down.
        socket=diff(block(0,20,0,12,0,10),[block(6-g,14+g,-.1,5.7,3-g,7+g)])
        pin=union([block(-8,8,-6,6,0,2.4),transform(peg(0,0,2.4),np.linalg.inv(SIGN))])
        for j,(label,m) in enumerate([('rail',fem),('panel',male),('socket',socket),('peg',pin)]):
            if label=='socket':
                inv=np.diag([1,-1,-1,1]); m=transform(m,inv)
            parts=normalized({3:m},IDENTITY)
            name=f'{label}_gap_{g:.2f}'
            entries.append((name,parts,1,(55+i*65,45+j*43,0)))
            list(parts.values())[0].export(OUT/'coupons'/f'{name}.stl')
            results.append({'name':name,'each_side_clearance_mm':g,'watertight':bool(m.is_watertight)})
    project(OUT/'Fit-coupons.3mf',entries)
    return results


def preview():
    # Save exact geometry for optional Blender cutaway rendering; only the preview roof is cut.
    from matplotlib.colors import to_rgba
    data=[]
    for it in items:
        for c,m in it['parts'].items():
            if it['plate']==2: m=diff(m,[block(-104,104,30,104,83.9,93)])
            data.append({'name':it['name']+' '+str(c),'vertices':m.vertices.tolist(),'faces':m.faces.tolist(),'rgba':to_rgba(COLORS[c]),'plate':it['plate'],'color':c,'base_color':next(iter(it['parts']))})
    (OUT/'preview-meshes.json').write_text(json.dumps(data))
    fig,ax=plt.subplots(figsize=(11,10))
    for it in items:
        b=tm.util.concatenate(list(it['parts'].values())).bounds
        if it['plate']==1: continue
        from matplotlib.patches import Rectangle
        ax.add_patch(Rectangle(b[0,:2],*(b[1,:2]-b[0,:2]),fill=False,edgecolor=COLORS[5] if it['plate'] in [3,4,6] else '#555555',linewidth=1.7))
        if it['plate'] in [3,4,6]:
            x=(b[0,0]+b[1,0])/2; ax.annotate('',(x,b[0,1]-30),(x,b[0,1]),arrowprops={'arrowstyle':'->','color':'#0066CC','lw':2})
    ax.set(xlim=(-115,115),ylim=(-115,115),xlabel='X / mm',ylabel='Y / mm',title='Top view: blue arrows = brand module extraction (-Y)')
    ax.set_aspect('equal'); ax.grid(alpha=.2); fig.savefig(OUT/'interface-plan.png',dpi=150); plt.close(fig)


def validate():
    report={'status':'ENGINEERING DRAFT - physical fit untested','per_side_clearance_mm':GAP,'parts':[],'assembly_collisions':[],'extraction_collisions':[]}
    solids={}
    for i,it in enumerate(items):
        ms=list(it['parts'].values())
        for c,m in it['parts'].items():
            assert m.is_watertight and m.is_volume,(it['name'],c)
        solid=union(ms); solids[i]=solid
        overlap=sum(m.volume for m in ms)-solid.volume
        assert abs(overlap)<.05,(it['name'],overlap)
        report['parts'].append({'name':it['name'],'plate':it['plate'],'bounds_mm':solid.bounds.tolist(),'all_color_meshes_watertight':True,'color_overlap_mm3':float(overlap)})
    def intersection(a,b):
        if np.any(a.bounds[1]<=b.bounds[0]+1e-5) or np.any(b.bounds[1]<=a.bounds[0]+1e-5): return 0.
        # Tangential contact can have zero volume and undefined center of mass.
        with np.errstate(invalid='ignore',divide='ignore'):
            result=tm.boolean.intersection([a,b],engine='manifold')
            volume=0. if len(result.faces)==0 else abs(result.volume)
        assert np.isfinite(volume)
        return volume
    for i,a in solids.items():
        for j,b in solids.items():
            if j<=i: continue
            v=intersection(a,b)
            if v>.05: report['assembly_collisions'].append([items[i]['name'],items[j]['name'],float(v)])
    # Full extraction sweep sampled every 2 mm; no promise of continuous collision proof.
    for i,it in enumerate(items):
        if it['plate'] not in [3,4,6]: continue
        travel={3:82,6:74}.get(it['plate'],10 if 'front fascia' in it['name'] else 86)
        # Once clear of guides, lift instead of dragging into the parking stops.
        path=[(float(d),0.) for d in range(2,travel+1,2)]+[(float(travel),float(h)) for h in range(2,22,2)]
        for distance,lift in path:
            a=move(solids[i],(0,-distance,lift))
            for j,b in solids.items():
                if i==j: continue
                v=intersection(a,b)
                if v>.05:
                    report['extraction_collisions'].append([it['name'],items[j]['name'],float(distance),float(v)])
                    break
            if report['extraction_collisions'] and report['extraction_collisions'][-1][0]==it['name']: break
    return report


def main():
    for d in [OUT,OUT/'stl',OUT/'coupons']: d.mkdir(parents=True,exist_ok=True)
    build(); report=validate()
    (OUT/'validation.json').write_text(json.dumps(report,indent=2))
    assert not report['assembly_collisions'],report['assembly_collisions']
    assert not report['extraction_collisions'],report['extraction_collisions']
    # Standard six-bed arrangement: 256 mm beds, pitch 307.2.
    centers={1:(128,128),2:(435.2,128),3:(742.4,128),4:(128,-179.2),5:(435.2,-179.2),6:(742.4,-179.2)}
    layouts={1:[(0,0)],2:[(0,0)],3:[(-47,0),(47,0)],4:[(0,-28),(0,25)],5:[(-64,0),(-32,0),(0,0),(32,0),(64,0)],6:[(0,0)]}
    counts={p:0 for p in range(1,7)}; entries=[]
    for it in items:
        p=it['plate']; xy=layouts[p][counts[p]]; counts[p]+=1
        parts=normalized(it['parts'],it['print_matrix'])
        bounds=tm.util.concatenate(list(parts.values())).bounds
        assert np.all(bounds[0,:2]+xy>=-125) and np.all(bounds[1,:2]+xy<=125)
        center=centers[p]
        entries.append((it['name'],parts,p,(center[0]+xy[0],center[1]+xy[1],0)))
        for color,m in parts.items(): m.export(OUT/'stl'/f"P{p}_{counts[p]}_filament{color}.stl")
    project(OUT/'BMW-Modular-V2-DRAFT.3mf',entries)
    # Blank brand surfaces have the identical mating solid: branding is flush, not structural.
    blank=[]
    for name,parts,p,offset in entries:
        if p in [3,4,6]:
            blank.append((name.replace('BMW','BRAND TEMPLATE'),{4:union(list(parts.values()))},p,offset))
        else: blank.append((name,parts,p,offset))
    project(OUT/'Brand-Template-V2-DRAFT.3mf',blank)
    report['brand_template']={'shared_plates':[1,2,5],'brand_plates':[3,4,6],'universal_meshes_shared_in_memory':True,'brand_mating_envelopes_identical':True}
    assembly=[(it['name'],it['parts'],1,(0,0,0)) for it in items]
    project(OUT/'Assembly-VIEW-ONLY.3mf',assembly)
    report['coupons']=coupons()
    (OUT/'validation.json').write_text(json.dumps(report,indent=2))
    preview()
    print('Generated six-plate draft, assembly, coupons, STL and validation report.')

if __name__=='__main__': main()
