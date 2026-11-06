"""Export STLs and a multi-colour Bambu-flavoured 3MF from the FCStd objects."""
import json
import os
import uuid
import zipfile
import FreeCAD as App
import Mesh

LAYER_FILES = [
    ('Paper_Base', 'paper_base.stl', 'paper'),
    ('Ruled_Lines_Grooves', 'gray_ruled_lines_inlay.stl', 'ruled_gray'),
    ('Handwriting_Raised', 'blue_handwriting.stl', 'handwriting_blue'),
    ('Date_Raised', 'black_date.stl', 'date_black'),
]


def _mesh_triangles(shape, tolerance=0.05):
    points, facets = shape.tessellate(tolerance)
    verts = [(p.x, p.y, p.z) for p in points]
    tris = [list(f) for f in facets]
    return verts, tris


def _fmt(v):
    return ('%.4f' % v).rstrip('0').rstrip('.')


def export_stls(doc, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    for name, filename, _ in LAYER_FILES:
        obj = doc.getObject(name)
        if obj is None or obj.Shape.isNull() or not obj.Shape.isValid():
            raise RuntimeError('cannot export %s: missing or invalid' % name)
        Mesh.export([obj], os.path.join(out_dir, filename))


def export_3mf(doc, cfg, out_path):
    extruder = {key: i + 1 for i, key in enumerate(cfg['extruder_order'])}
    objects_xml = []
    settings_objects = []
    instances = []

    for obj_id, (name, filename, color_key) in enumerate(LAYER_FILES, start=1):
        obj = doc.getObject(name)
        verts, tris = _mesh_triangles(obj.Shape)
        vxml = ''.join('<vertex x="%s" y="%s" z="%s"/>' % (_fmt(v[0]), _fmt(v[1]), _fmt(v[2])) for v in verts)
        txml = ''.join('<triangle v1="%d" v2="%d" v3="%d"/>' % (a, b, c) for a, b, c in tris)
        objects_xml.append(
            '  <object id="%d" type="model" uuid="%s">\n'
            '   <metadata name="Name">%s</metadata>\n'
            '   <mesh>\n    <vertices>\n%s\n    </vertices>\n    <triangles>\n%s\n    </triangles>\n   </mesh>\n'
            '  </object>\n' % (obj_id, uuid.uuid4(), filename, vxml, txml))
        part_uuid = uuid.uuid4()
        settings_objects.append(
            '  <object id="%d">\n'
            '    <metadata key="name" value="%s"/>\n'
            '    <metadata key="extruder" value="%d"/>\n'
            '    <metadata face_count="%d"/>\n'
            '    <part id="1" subtype="normal_part" uuid="%s">\n'
            '      <metadata key="name" value="%s"/>\n'
            '      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>\n'
            '      <metadata key="source_file" value="%s"/>\n'
            '      <metadata key="extruder" value="%d"/>\n'
            '      <mesh_stat face_count="%d" edges_fixed="0" degenerate_facets="0" facets_removed="0" facets_reversed="0" backwards_edges="0"/>\n'
            '    </part>\n'
            '  </object>\n'
            % (obj_id, filename, extruder[color_key], len(tris), part_uuid,
               filename, filename, extruder[color_key], len(tris)))
        instances.append(
            '    <model_instance>\n'
            '      <metadata key="object_id" value="%d"/>\n'
            '      <metadata key="instance_id" value="0"/>\n'
            '      <metadata key="identify_id" value="%d"/>\n'
            '    </model_instance>\n' % (obj_id, 1000 + obj_id))

    model_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">\n'
        ' <metadata name="Application">handwriting-nameplate-pipeline</metadata>\n'
        ' <resources>\n%s </resources>\n'
        ' <build>\n%s </build>\n'
        '</model>\n'
        % (''.join(objects_xml),
           ''.join('  <item objectid="%d" transform="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>\n' % i
                   for i in range(1, len(LAYER_FILES) + 1))))

    settings_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n<config>\n%s <plate>\n'
        '    <metadata key="plater_id" value="1"/>\n'
        '    <metadata key="plater_name" value=""/>\n'
        '    <metadata key="locked" value="false"/>\n'
        '%s  </plate>\n</config>\n'
        % (''.join(settings_objects), ''.join(instances)))

    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
        ' <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
        ' <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>\n'
        ' <Default Extension="png" ContentType="image/png"/>\n'
        '</Types>\n')

    root_rels = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
        ' <Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n'
        '</Relationships>\n')

    slice_info = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<config>\n  <header>\n'
        '    <header_item key="X-BBL-Client-Type" value="slicer"/>\n'
        '    <header_item key="X-BBL-Client-Version" value="pipeline"/>\n'
        '  </header>\n</config>\n')

    with zipfile.ZipFile(out_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('[Content_Types].xml', content_types)
        zf.writestr('_rels/.rels', root_rels)
        zf.writestr('3D/3dmodel.model', model_xml)
        zf.writestr('Metadata/model_settings.config', settings_xml)
        zf.writestr('Metadata/slice_info.config', slice_info)
        zf.writestr('Metadata/filament_sequence.json',
                    json.dumps({'plate_1': {'nozzle_sequence': [], 'optimal_assignment': [], 'sequence': []}}))
    return out_path
