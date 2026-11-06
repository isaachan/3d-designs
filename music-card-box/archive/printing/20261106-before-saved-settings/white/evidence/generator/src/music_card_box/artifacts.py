"""Portable millimetre/color 3MF geometry; intentionally no printer preset."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import xml.etree.ElementTree as ET
import hashlib
import json

NS='http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
ET.register_namespace('',NS)
def tag(name): return '{'+NS+'}'+name

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def write_json(path,content):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json.dumps(content,ensure_ascii=False,indent=2)+'\n')

def mesh_data(shape):
    import MeshPart
    mesh=MeshPart.meshFromShape(Shape=shape,LinearDeflection=.07,AngularDeflection=.12,Relative=False)
    vertices,faces=mesh.Topology
    return mesh,[[float(c) for c in v] for v in vertices],[list(f) for f in faces]

def export_3mf(path,objects,colors):
    model=ET.Element(tag('model'),{'unit':'millimeter','xml:lang':'en-US'})
    ET.SubElement(model,tag('metadata'),{'name':'Application'}).text='music-card-box r1'
    resources=ET.SubElement(model,tag('resources'))
    bases=ET.SubElement(resources,tag('basematerials'),{'id':'1'})
    keys=list(colors)
    for key in keys: ET.SubElement(bases,tag('base'),{'name':key,'displaycolor':colors[key]+'FF'})
    build=ET.SubElement(model,tag('build'))
    for index,obj in enumerate(objects,2):
        entry=ET.SubElement(resources,tag('object'),{'id':str(index),'type':'model','name':obj['name'],
            'pid':'1','pindex':str(keys.index(obj['color']))})
        mesh=ET.SubElement(entry,tag('mesh'))
        verts=ET.SubElement(mesh,tag('vertices'))
        for v in obj['vertices']: ET.SubElement(verts,tag('vertex'),dict(zip(('x','y','z'),(f'{c:.7f}' for c in v))))
        tris=ET.SubElement(mesh,tag('triangles'))
        for face in obj['faces']: ET.SubElement(tris,tag('triangle'),dict(zip(('v1','v2','v3'),map(str,face))))
        ET.SubElement(build,tag('item'),{'objectid':str(index)})
    with ZipFile(path,'w',ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml','<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
        z.writestr('_rels/.rels','<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
        z.writestr('3D/3dmodel.model',ET.tostring(model,encoding='utf-8',xml_declaration=True))

def print_vertices(vertices,name,depth,wall,gap,panel_thickness):
    if name=='CassetteShell':
        return [[x+110,y+15,z] for x,y,z in vertices]
    back_y=depth+gap
    if name=='MusicNote': back_y+=panel_thickness+gap
    # Every decorative part has its actual glue face flat on the bed.
    centers={'SkyPanel':(110,85),'ReelLeft':(100,90),'ReelRight':(60,90),
             'TapeBadge':(110,35),'MusicNote':(110,85)}
    cx,cz=centers[name]
    # Remove assembly X offset for duplicate reels.
    offset={'ReelLeft':-47,'ReelRight':47}.get(name,0)
    # A proper +90 degree X rotation preserves outward triangle winding.
    return [[x-offset+cx,-z+cz,y-back_y] for x,y,z in vertices]
