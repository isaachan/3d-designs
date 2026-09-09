"""Create a one-plate, five-colour 20 x 40 mm orientation comparison."""
from pathlib import Path
import json
import math
import zipfile
import xml.etree.ElementTree as ET

import numpy as np
import trimesh
import manifold3d
from PIL import Image, ImageDraw
from shapely.geometry import Polygon
import generate_plaques as g

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'angle-test'
CORE = 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
ET.register_namespace('', CORE)


def node(parent, tag, **attrs):
    return ET.SubElement(parent, tag, {k: str(v) for k, v in attrs.items()})


def boolean(meshes, intersect=False):
    solids = [manifold3d.Manifold(manifold3d.Mesh(np.float32(m.vertices), np.uint32(m.faces))) for m in meshes]
    result = solids[0]
    for solid in solids[1:]:
        result = result ^ solid if intersect else result + solid
    mesh = result.to_mesh()
    return trimesh.Trimesh(mesh.vert_properties, mesh.tri_verts, process=False)


def profile(kind, name):
    folder = Path('/Applications/BambuStudio.app/Contents/Resources/profiles/BBL') / kind
    data = json.loads((folder / (name + '.json')).read_text())
    base = profile(kind, data['inherits']) if data.get('inherits') else {}
    for include in data.get('include', []):
        base.update(profile(kind, include))
    base.update(data)
    return base


def main():
    OUT.mkdir(exist_ok=True)
    # Coordinates in the unchanged full-sized EN plaque: moon and stacked books.
    clip = trimesh.creation.box([20, 40, 5])
    clip.apply_translation([-98, 0, 1.5])
    pieces = {}
    for colour in g.COLOR_ORDER:
        source = trimesh.load_mesh(ROOT / 'generated/EN' / f'HankLibrary-EN-{colour}.stl')
        mesh = boolean([source, clip], intersect=True)
        assert mesh.is_volume and len(mesh.faces), colour
        mesh.apply_translation([98, 20, 0])  # bottom artwork edge is now y=0
        pieces[colour] = mesh

    model = ET.Element('model', {'unit': 'millimeter', 'xmlns': CORE})
    node(model, 'metadata', name='Application').text = 'BambuStudio-02.08.02.61'
    node(model, 'metadata', name='BambuStudio:3mfVersion').text = '1'
    resources = node(model, 'resources')
    materials = node(resources, 'basematerials', id=100)
    for colour in g.COLOR_ORDER:
        node(materials, 'base', name=colour, displaycolor='#%02X%02X%02XFF' % g.DISPLAY_RGB[colour])
    build = node(model, 'build')
    config = ET.Element('config')
    plate = node(config, 'plate')
    node(plate, 'metadata', key='plater_id', value=1)
    node(plate, 'metadata', key='plater_name', value='EN angle test: 90 - 80 - 70')
    reports = []
    for index, angle in enumerate([90, 80, 70]):
        rad = math.radians(angle)
        rotation = trimesh.transformations.rotation_matrix(rad, [1, 0, 0])
        meshes = {}
        for colour, original in pieces.items():
            m = original.copy()
            m.apply_transform(rotation)
            m.apply_translation([0, 0, 0.6])
            meshes[colour] = m
        # A wedge fills underneath the rotated bottom edge, without changing the art.
        yz = Polygon([(0, .59), (-3*math.sin(rad), .59),
                      (-3*math.sin(rad), .6+3*math.cos(rad)), (0, .6)])
        wedge = g.extrude_geometry(yz, 20)
        wedge.vertices = wedge.vertices[:, [2, 0, 1]]
        wedge.apply_translation([-10, 0, 0])
        foot = trimesh.creation.box([26, 14, .6])
        foot.apply_translation([0, -1.5, .3])
        meshes['blue'] = boolean([meshes['blue'], wedge, foot])
        assembly_id = 10 + index*10
        obj_config = node(config, 'object', id=assembly_id)
        node(obj_config, 'metadata', key='name', value=f'EN_{angle}deg_20x40mm')
        node(obj_config, 'metadata', key='extruder', value=1)
        ids = []
        for colour_index, colour in enumerate(g.COLOR_ORDER):
            mesh = meshes[colour]
            assert mesh.is_volume and mesh.is_watertight, (angle, colour)
            oid = assembly_id + colour_index + 1
            ids.append(oid)
            obj = node(resources, 'object', id=oid, type='model', name=colour,
                       pid=100, pindex=colour_index)
            mesh_xml = node(obj, 'mesh')
            vertices = node(mesh_xml, 'vertices')
            for v in mesh.vertices:
                node(vertices, 'vertex', x=f'{v[0]:.7f}', y=f'{v[1]:.7f}', z=f'{v[2]:.7f}')
            triangles = node(mesh_xml, 'triangles')
            for f in mesh.faces:
                node(triangles, 'triangle', v1=f[0], v2=f[1], v3=f[2])
            part = node(obj_config, 'part', id=oid, subtype='normal_part')
            node(part, 'metadata', key='name', value=f'{angle}deg_{colour}')
            node(part, 'metadata', key='extruder', value=colour_index+1)
        assembly = node(resources, 'object', id=assembly_id, type='model', name=f'EN_{angle}deg')
        components = node(assembly, 'components')
        for oid in ids:
            node(components, 'component', objectid=oid)
        x, y = 80+index*43, 100
        node(build, 'item', objectid=assembly_id, transform=f'1 0 0 0 1 0 0 0 1 {x} {y} 0', printable=1)
        inst = node(plate, 'model_instance')
        for key, value in [('object_id', assembly_id), ('instance_id', 0), ('identify_id', index+1)]:
            node(inst, 'metadata', key=key, value=value)
        bounds = trimesh.util.concatenate(list(meshes.values())).bounds
        reports.append({'angle': angle, 'position_xy': [x,y], 'bounds_local': bounds.tolist(),
                        'all_five_parts_watertight': True})

    machine_name = 'Bambu Lab X2D 0.4 nozzle'
    process_name = '0.20mm Standard @BBL X2D'
    filament_name = 'Bambu PLA Basic @BBL X2D 0.4 nozzle'
    settings = profile('machine', machine_name)
    settings.update(profile('process', process_name))
    filament = profile('filament', filament_name)
    for key, value in filament.items():
        if key not in ('inherits', 'name', 'type', 'from', 'instantiation', 'setting_id'):
            settings[key] = value*5 if isinstance(value, list) and len(value) in (1,6) else value
    for key in ['inherits', 'include', 'name', 'type', 'from', 'instantiation', 'setting_id']:
        settings.pop(key, None)
    settings.update({'printer_settings_id':machine_name, 'print_settings_id':process_name,
                     'filament_settings_id':[filament_name]*5, 'filament_type':['PLA']*5,
                     'filament_is_support':['0']*5,
                     'filament_self_index':[str(i) for i in range(1,6) for _ in range(6)],
                     'filament_colour':['#%02X%02X%02X' % g.DISPLAY_RGB[c] for c in g.COLOR_ORDER],
                     'layer_height':'0.2', 'initial_layer_print_height':'0.2',
                     'enable_support':'0', 'brim_type':'outer_only', 'brim_width':'4',
                     'brim_object_gap':'0.1', 'enable_prime_tower':'1',
                     'print_sequence':'by layer', 'filament_map':['1','1','1','2','1'],
                     'filament_map_mode':'Auto For Flush'})
    target = OUT / 'HankLibrary-EN-angle-test-90-80-70.3mf'
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/><Default Extension="config" ContentType="application/octet-stream"/></Types>')
        z.writestr('_rels/.rels', '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
        z.writestr('3D/3dmodel.model', ET.tostring(model, encoding='utf-8', xml_declaration=True))
        z.writestr('Metadata/model_settings.config', ET.tostring(config, encoding='utf-8', xml_declaration=True))
        z.writestr('Metadata/project_settings.config', json.dumps(settings))
    (OUT/'validation.json').write_text(json.dumps(reports, indent=2))
    image = Image.open(ROOT/'generated/EN/HankLibrary-EN-preview.png')
    # Existing preview is 6 pixels/mm; crop same coordinates as the 3D clip.
    image.crop((72,30,192,270)).resize((240,480)).save(OUT/'crop-preview.png')
    print(target)
    print(json.dumps(reports, indent=2))


if __name__ == '__main__':
    main()
