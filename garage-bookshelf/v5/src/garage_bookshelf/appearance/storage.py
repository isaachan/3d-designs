"""Preserve saved FreeCAD view providers when editing with headless Python.

Only GuiDocument.xml and its appearance resources are changed. Native geometry,
feature definitions, placements and constraints remain owned by FreeCAD.
"""
import collections
import copy
import struct
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED


def material_records(raw):
    count, = struct.unpack_from('<I', raw)
    # FreeCAD writes all fixed-size material data first, then each material's
    # variable-size image/path/UUID strings. A one-material file hides this
    # distinction, so parse and serialize multi-face arrays explicitly.
    cursor, records = 4+24*count, []
    for i in range(count):
        start = cursor
        for _ in range(3):  # image, image path, material UUID
            size, = struct.unpack_from('<I', raw, cursor)
            cursor += 4+size
        records.append(raw[4+24*i:4+24*(i+1)]+raw[start:cursor])
    assert cursor == len(raw), (cursor, len(raw))
    return records


def serialize_material_records(records):
    return struct.pack('<I', len(records))+b''.join(r[:24] for r in records)+b''.join(r[24:] for r in records)


def diffuse_rgb(record):
    value, = struct.unpack_from('<I', record, 4)
    return tuple(((value >> shift) & 255)/255 for shift in (24, 16, 8))


def _property(provider, name):
    return next(p for p in provider.iter('Property') if p.attrib.get('name') == name)


def _visibility(provider, visible):
    _property(provider, 'Visibility')[0].set('value', 'true' if visible else 'false')


def preserve_views(source, output, doc, changed_bodies):
    from garage_bookshelf.parking.markings import face_colors
    from garage_bookshelf.parameters import evaluate
    with ZipFile(source) as archive:
        saved = {name: archive.read(name) for name in archive.namelist()}
    for name, raw in saved.items():
        if name.startswith('ShapeAppearance'):
            assert serialize_material_records(material_records(raw)) == raw, name
    root = ET.fromstring(saved['GuiDocument.xml'])
    data = root.find('ViewProviderData')
    providers = {p.attrib['name']: p for p in data}
    # Body material is a base-color reference; keep all unrelated view data exact.
    body_provider = providers['module_2_Body']
    material_file = _property(body_provider, 'ShapeAppearance')[0].attrib['file']
    base_record = material_records(saved[material_file])[0]
    gray = diffuse_rgb(base_record)
    template_names = {
        'App::Part': 'garage_deck_1',
        'PartDesign::Body': 'garage_deck_1_Body',
        'Sketcher::SketchObject': 'Sketch_WholeDeck',
        'PartDesign::Pad': 'Pad_WholeDeck',
        'PartDesign::Pocket': 'Pocket_FourLocatingHoles',
        'PartDesign::Chamfer': 'Fillet_ExposedCorners003',
    }
    original_types = collections.defaultdict(list)
    for obj in doc.Objects:
        if obj.Name in providers:
            original_types[obj.TypeId].append(obj.Name)
    new = []
    for obj in doc.Objects:
        if obj.Name in providers:
            continue
        if obj.TypeId in template_names:
            template = template_names[obj.TypeId]
        else:
            candidates = original_types.get(obj.TypeId, [])
            assert candidates, (obj.Name, obj.TypeId)
            template = candidates[0]
        provider = copy.deepcopy(providers[template])
        provider.set('name', obj.Name)
        provider.set('expanded', '0')
        _visibility(provider, False)
        data.append(provider)
        providers[obj.Name] = provider
        new.append(obj.Name)
    resources = {}
    counts = {}
    for name in changed_bodies:
        body = doc.getObject(name)
        colors = face_colors(body, gray) if 'ParkingBays' in body.PropertiesList else [gray]*len(body.Shape.Faces)
        if 'TrayRecessCount' in body.PropertiesList:
            top = evaluate(doc, 'BaseThickness' if body.SourcePart == 'module_1' else 'DeckThickness')
            floor = top-evaluate(doc, 'ParkingRecessDepth')
            colors = [tuple(c*.86 for c in gray)
                if face.normalAt(0, 0).z > .99 and abs(face.CenterOfMass.z-floor) < 1e-6 else rgb
                for face, rgb in zip(body.Shape.Faces, colors)]
        assert len(colors) == len(body.Shape.Faces)
        records = []
        for rgb in colors:
            record = bytearray(base_record)
            rgba = sum(round(c*255) << shift for c, shift in zip(rgb, (24, 16, 8))) | 255
            struct.pack_into('<I', record, 4, rgba)
            records.append(bytes(record))
        file = f'ParkingAppearance_{name}.bin'
        resources[file] = serialize_material_records(records)
        for obj in [body, body.Tip]:
            vp = providers[obj.Name]
            _property(vp, 'ShapeAppearance')[0].set('file', file)
            for prop in ('LineColorArray', 'PointColorArray'):
                empty = f'ParkingEmpty_{prop}.bin'
                _property(vp, prop)[0].set('file', empty)
                resources[empty] = struct.pack('<I', 0)
        for child in body.Group:
            if child.Name in providers:
                _visibility(providers[child.Name], child == body.Tip)
        _visibility(providers[name], True)
        counts[name] = len(records)
    # The interface sample stays in the actual receiving recess, hidden until
    # the user enables its dedicated group in the tree.
    sample_names = set()
    for obj in doc.Objects:
        if obj.Name == 'ParkingTraySamples' or obj.Name.startswith('parking_tray_interface'):
            sample_names.add(obj.Name)
    for name in sample_names:
        _visibility(providers[name], name != 'ParkingTraySamples')
    # Incremental decoration updates may replace old sketches and binders.
    # Remove only view providers whose native document objects were retired.
    retired=[]
    for name,provider in list(providers.items()):
        if doc.getObject(name) is None:
            data.remove(provider);del providers[name];retired.append(name)
    data.set('Count', str(len(providers)))
    # All original appearance assets referenced by the preserved XML must remain.
    referenced = {e.attrib['file'] for e in root.iter() if 'file' in e.attrib}
    for file in referenced:
        if file not in resources:
            resources[file] = saved[file]
    resources['GuiDocument.xml'] = ET.tostring(root, encoding='utf-8', xml_declaration=True)
    with ZipFile(output) as archive:
        result = {name: archive.read(name) for name in archive.namelist()}
    result.update(resources)
    temporary = output.with_suffix('.view.FCStd')
    with ZipFile(temporary, 'w', ZIP_DEFLATED) as archive:
        for name, raw in result.items():
            archive.writestr(name, raw)
    temporary.replace(output)
    with ZipFile(output) as archive:
        assert archive.testzip() is None
        loaded = ET.fromstring(archive.read('GuiDocument.xml'))
        assert len(list(loaded.find('ViewProviderData'))) == len(providers)
        for name, count in counts.items():
            assert len(material_records(archive.read(f'ParkingAppearance_{name}.bin'))) == count
    return dict(preserved_original_view_providers=True, new_view_provider_count=len(new),
        retired_view_provider_count=len(retired),
        native_view_provider_count=len(providers), updated_face_material_counts=counts,
        sample_group_default_visible=False, zip_crc_check='passed')
