"""Convert the supplied Bambu project, preserving structural meshes and plate placement.
Run: .venv/bin/python convert_to_bmw.py
"""
from pathlib import Path
import copy, json, uuid, zipfile, xml.etree.ElementTree as ET
import numpy as np
import trimesh
from shapely.geometry import Polygon, Point, box
from shapely.ops import unary_union
from shapely import affinity
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch
from matplotlib.path import Path as MPath

HERE = Path(__file__).resolve().parent
CORE = 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
PROD = 'http://schemas.microsoft.com/3dmanufacturing/production/2015/06'
BAMBU = 'http://schemas.bambulab.com/package/2021'
ET.register_namespace('', CORE)
ET.register_namespace('p', PROD)
ET.register_namespace('BambuStudio', BAMBU)
NS = {'m': CORE}
def tag(s): return '{'+CORE+'}'+s

def polygons(g):
    if g.is_empty: return []
    return [g] if g.geom_type == 'Polygon' else [p for sub in g.geoms for p in polygons(sub)]

def text(s, x, y, width, height):
    outlines = TextPath((0, 0), s, size=20, prop=FontProperties(family='DejaVu Sans', weight='bold')).to_polygons()
    g = Polygon()
    for p in outlines: g = g.symmetric_difference(Polygon(p))
    a,b,c,d = g.bounds
    g = affinity.translate(g, -a, -b)
    g = affinity.scale(g, width/(c-a), height/(d-b), origin=(0,0))
    return affinity.translate(g, x, y)

def roundel(x,y,r):
    outer = Point(x,y).buffer(r, quad_segs=64)
    inner = Point(x,y).buffer(r*.64, quad_segs=64)
    rim = outer.difference(Point(x,y).buffer(r*.94, quad_segs=64))
    blue = inner.intersection(unary_union([box(x,y,x+r,y+r),box(x-r,y-r,x,y)]))
    white = unary_union([rim, inner.difference(blue)])
    # Legible simplified BMW lettering in the black upper ring.
    white = white.union(text('BMW',x-r*.40,y+r*.69,r*.80,r*.15))
    return {1: outer.difference(white.union(blue)), 4: white, 5: blue}

def artwork(kind):
    layers={1:[],4:[],5:[]}
    def logo(x,y,r):
        for c,g in roundel(x,y,r).items(): layers[c].append(g)
    if kind == 39:
        layers[4].append(text('BMW GARAGE',-89,-4.6,137,9.2))
        logo(84,0,8.7)
        layers[4].append(box(-89,-7.0,48,-6.3))
    elif kind == 42:
        logo(0,3,18)
        layers[4].append(text('BMW',-16,-24,32,6))
        layers[4].append(text('GARAGE',-18,-32,36,4))
    else:
        logo(-58,1.5,22)
        logo(47.5,0,26)
    return {c:unary_union(gs) for c,gs in layers.items() if gs}

def mesh_from_xml(root):
    vs=root.findall('.//m:vertex',NS); ts=root.findall('.//m:triangle',NS)
    return trimesh.Trimesh([[float(v.get(k)) for k in 'xyz'] for v in vs],[[int(t.get(k)) for k in ['v1','v2','v3']] for t in ts])

def extrude(g,z,depth):
    meshes=[]
    for p in polygons(g):
        m=trimesh.creation.extrude_polygon(p,depth,engine='earcut'); m.apply_translation((0,0,z)); meshes.append(m)
    return trimesh.util.concatenate(meshes)

def put_mesh(obj,m):
    el=ET.SubElement(obj,tag('mesh')); vs=ET.SubElement(el,tag('vertices')); ts=ET.SubElement(el,tag('triangles'))
    for v in m.vertices: ET.SubElement(vs,tag('vertex'),dict(zip('xyz',(f'{a:.9g}' for a in v))))
    for f in m.faces: ET.SubElement(ts,tag('triangle'),dict(zip(['v1','v2','v3'],map(str,f))))

def xml(r): return ET.tostring(r,encoding='utf-8',xml_declaration=True)

def run():
    with zipfile.ZipFile(HERE/'Garage_Honda.3mf') as z: files={n:z.read(n) for n in z.namelist()}
    main=ET.fromstring(files['3D/3dmodel.model']); settings=ET.fromstring(files['Metadata/model_settings.config'])
    report={'source':'Garage_Honda.3mf','modified':[], 'preserved_meshes':[]}
    fig,axs=plt.subplots(3,1,figsize=(14,13),gridspec_kw={'height_ratios':[1,3,3]})
    palette={1:'#101318',4:'#FFFFFF',5:'#0066CC'}
    for ax,(fileid,oid,pid,base_color) in zip(axs,[(39,14,13,5),(42,16,15,5),(43,18,17,4)]):
        path=f'3D/Objects/object_{fileid}.model'; root=ET.fromstring(files[path]); original=mesh_from_xml(root)
        flat=original.copy(); top=float(flat.bounds[1,2]); bottom=float(flat.bounds[0,2])
        # Remove Honda's shallow relief, retaining the actual mounting profile/backside.
        footprint=unary_union([Polygon(t[:,:2]) for t in original.triangles if Polygon(t[:,:2]).area>1e-10])
        cap=extrude(footprint,top-.1,.1)
        flat=trimesh.boolean.union([original,cap],engine='manifold')
        assert flat.is_watertight and flat.is_volume
        art=artwork(fileid); art={c:g for c,g in art.items() if c!=base_color}
        inserts={c:extrude(g,top-.4,.4) for c,g in art.items()}
        cutters=[extrude(g,top-.4,.5) for g in art.values()]
        backing=trimesh.boolean.difference([flat,*cutters],engine='manifold')
        allparts=[(pid,base_color,backing,'panel')]+[(fileid*100+c,c,m,'inlay') for c,m in inserts.items()]
        # Check that colored regions partition the solid without changing its envelope.
        assembled=trimesh.boolean.union([m for _,_,m,_ in allparts],engine='manifold')
        error=abs(assembled.volume-flat.volume)
        assert error<.02, (fileid,error)
        assert np.allclose(assembled.bounds,original.bounds,atol=1e-5)
        resources=root.find('m:resources',NS); resources.clear()
        mainobj=main.find(f"m:resources/m:object[@id='{oid}']",NS); components=mainobj.find('m:components',NS)
        oldcomp=copy.deepcopy(components[0]); components.clear()
        cfg=settings.find(f"object[@id='{oid}']"); template=copy.deepcopy(cfg.find('part'))
        for p in list(cfg.findall('part')): cfg.remove(p)
        title={39:'BMW GARAGE - front fascia',42:'BMW - interior sign',43:'BMW - glass partitions'}[fileid]
        cfg.find("metadata[@key='name']").set('value',title)
        cfg.find("metadata[@key='extruder']").set('value',str(base_color))
        cfg.find('metadata[@face_count]').set('face_count',str(sum(len(m.faces) for _,_,m,_ in allparts)))
        details=[]
        for newpid,color,m,label in allparts:
            assert m.is_watertight and m.is_volume
            obj=ET.SubElement(resources,tag('object'),{'id':str(newpid),'type':'model','name':f'{title} {label} {color}', '{'+PROD+'}UUID':str(uuid.uuid4())}); put_mesh(obj,m)
            comp=copy.deepcopy(oldcomp); comp.set('objectid',str(newpid)); comp.set('{'+PROD+'}UUID',str(uuid.uuid4())); components.append(comp)
            part=copy.deepcopy(template); part.set('id',str(newpid)); part.set('uuid',str(uuid.uuid4()))
            for meta in list(part.findall('metadata')):
                key=meta.get('key')
                if key=='name': meta.set('value',f'{title} {label} / {color}')
                elif key!='matrix': part.remove(meta)
            ET.SubElement(part,'metadata',{'key':'extruder','value':str(color)})
            part.find('mesh_stat').set('face_count',str(len(m.faces))); cfg.append(part)
            details.append({'id':newpid,'filament':color,'triangles':len(m.faces),'watertight':bool(m.is_watertight)})
        files[path]=xml(root)
        report['modified'].append({'file':path,'bounds_mm':original.bounds.tolist(),'volume_difference_mm3':error,'parts':details})
        # Preview in local face coordinates, not a misleading original Honda thumbnail.
        outline=unary_union([Polygon(t[:,:2]) for t in flat.triangles if np.allclose(t[:,2],top)])
        def draw(g,color):
            for p in polygons(g):
                rings=[p.exterior,*p.interiors]; vertices=[]; codes=[]
                for ring in rings:
                    xy=list(ring.coords); vertices.extend(xy); codes.extend([MPath.MOVETO]+[MPath.LINETO]*(len(xy)-2)+[MPath.CLOSEPOLY])
                ax.add_patch(PathPatch(MPath(vertices,codes),facecolor=color,edgecolor='none'))
        draw(outline,palette[base_color])
        for color,g in art.items(): draw(g,palette[color])
        ax.autoscale_view(); ax.set_aspect('equal'); ax.set_facecolor('#D9DEE5'); ax.set_title(title); ax.set_xlabel('mm'); ax.set_ylabel('mm')
    fig.tight_layout(); fig.savefig(HERE/'BMW-panels-preview.png',dpi=160)
    for m in main.findall('m:metadata',NS):
        name=m.get('name')
        if name=='Title': m.text='BMW Garage – 1:64 (modified Honda project)'
        elif name=='Description': m.text='BMW-themed derivative: front fascia, interior sign and two partitions replaced. Original structure, mounting envelopes and six print plates retained. Re-slice before printing.'
        elif name=='ProfileTitle': m.text='BMW Garage - modified, not print-tested'
    # Keep original designer and license attribution; remove stale cached assembly-volume transforms.
    assembly=settings.find('assemble')
    if assembly is not None: settings.remove(assembly)
    for meta in settings.findall('.//metadata'):
        if meta.get('key')=='source_file': meta.set('value','Garage_BMW.3mf')
        if meta.get('key')=='plater_name' and meta.get('value')=='Inside and front logo': meta.set('value','BMW interior and front signs')
    ps=json.loads(files['Metadata/project_settings.config'])
    for key in ['filament_colour','filament_multi_colour']:
        ps[key][4]='#0066CC'
    files['Metadata/project_settings.config']=json.dumps(ps,ensure_ascii=False,indent=2).encode()
    files['3D/3dmodel.model']=xml(main); files['Metadata/model_settings.config']=xml(settings)
    # Old photos and thumbnails show Honda. Drop them and their references instead of claiming a new render.
    removed={n for n in files if n.startswith('Auxiliaries/') or (n.startswith('Metadata/') and n.endswith(('.png','.json')))}
    removed -= {'Metadata/filament_sequence.json'}
    for n in removed: del files[n]
    for meta in list(main.findall('m:metadata',NS)):
        if meta.get('name') in ['Thumbnail_Middle','Thumbnail_Small','DesignerCover','ProfileCover']: main.remove(meta)
    for plate in settings.findall('plate'):
        for meta in list(plate.findall('metadata')):
            if meta.get('key') in ['thumbnail_file','thumbnail_no_light_file','top_file','pick_file']: plate.remove(meta)
    rel=ET.fromstring(files['_rels/.rels'])
    for r in list(rel):
        if r.get('Target','').lstrip('/') in removed: rel.remove(r)
    ET.register_namespace('', 'http://schemas.openxmlformats.org/package/2006/relationships')
    files['_rels/.rels']=xml(rel)
    ET.register_namespace('', CORE)
    files['3D/3dmodel.model']=xml(main); files['Metadata/model_settings.config']=xml(settings)
    with zipfile.ZipFile(HERE/'Garage_Honda.3mf') as src:
        for n,data in files.items():
            if n.startswith('3D/Objects/') and n not in [x['file'] for x in report['modified']]:
                assert data==src.read(n); report['preserved_meshes'].append(n)
    with zipfile.ZipFile(HERE/'Garage_BMW.3mf','w',zipfile.ZIP_DEFLATED) as z:
        for n,data in files.items(): z.writestr(n,data)
    (HERE/'validation.json').write_text(json.dumps(report,indent=2))
    print('Created Garage_BMW.3mf and BMW-panels-preview.png; geometry checks passed.')

if __name__=='__main__': run()
