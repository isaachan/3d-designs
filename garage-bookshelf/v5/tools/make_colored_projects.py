"""Transfer the current native CAD's face colours and M ribbons into real paint.

Run with FreeCAD Python. CAD, existing projects and filament presets are read
only. Each saved project is independently reopened and sliced with its own
settings. This generates Bambu paint data, not zero-thickness mesh overlays.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED
import _bootstrap
import FreeCAD as App
import MeshPart
import Part
from garage_bookshelf.assembly import global_shape
from garage_bookshelf.paths import CAD, ROOT, PROFILES, TMP, output_directory, sha, source_record, read_json, write_json
from garage_bookshelf.printing.bambu import run_cli
from garage_bookshelf.printing.manifests import verified_manifest
from garage_bookshelf.printing.paint import PALETTE, leaf, paint_triangle, paint_states
from garage_bookshelf.printing.threemf import NS, transform, project_bounds
from garage_bookshelf.rendering.software import saved_colors
from garage_bookshelf.specification import appearance_graphics

ET.register_namespace('', NS['c'])
ET.register_namespace('p', NS['p'])
ET.register_namespace('BambuStudio', 'http://schemas.bambulab.com/package/2021')


def key(points):
    return tuple(sorted(tuple(round(v, 3) for v in p) for p in points))


def nearest_color(rgb):
    # Recess black uses the same filament as the structural black.
    if max(rgb) < .2:
        return 1
    palette = [[int(hexcode[i:i+2], 16)/255 for i in (1, 3, 5)] for _, hexcode in PALETTE]
    state = min(range(len(palette)), key=lambda i: sum((a-b)**2 for a, b in zip(rgb, palette[i])))
    error = max(abs(a-b) for a, b in zip(rgb, palette[state]))
    assert error < .015, (rgb, state, error)
    return state+1


class CADPaint:
    def __init__(self, doc, geometry):
        self.doc, self.cache, self.backgrounds = doc, {}, {}
        self.records = {p['part']: p for p in geometry['print_parts']}
        self.colors = saved_colors(CAD)
        self.masks = []
        for obj in appearance_graphics(doc):
            state = next(i+1 for i, (name, _) in enumerate(PALETTE) if name == obj.MColor)
            normal = tuple(obj.DisplayNormal)
            axis = max(range(3), key=lambda i: abs(normal[i]))
            axes = [i for i in range(3) if i != axis]
            face = global_shape(obj.Base).Faces[0]
            points = [tuple(v.Point) for v in face.OuterWire.OrderedVertexes]
            plane = points[0][axis]
            polygon = [tuple(p[i] for i in axes) for p in points]
            self.masks.append(dict(state=state, axis=axis, axes=axes, normal=normal,
                                   plane=plane, polygon=polygon, source=obj.Name))

    def part(self, name):
        if name in self.cache:
            return self.cache[name]
        body = self.doc.getObject(name+'_Body')
        shape = global_shape(body)
        mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=.02, AngularDeflection=.12, Relative=False)
        colors = self.colors.get(body.Tip.Name, self.colors.get(body.Name))
        if len(colors) == 1:
            colors = colors*len(shape.Faces)
        assert len(colors) == len(shape.Faces), name
        lookup, areas, face_info = {}, defaultdict(float), []
        for face, rgb in zip(shape.Faces, colors):
            state = nearest_color(rgb)
            areas[state] += face.Area
            verts, triangles = face.tessellate(.02)
            normal = tuple(face.normalAt(0, 0))
            masks = [m for m in self.masks if
                     getattr(face.BoundBox, 'XYZ'[m['axis']]+'Length') < 1e-6 and
                     all(abs(p[m['axis']]-m['plane']) < 1e-6
                         for p in (tuple(face.CenterOfMass),)) and
                     sum(a*b for a, b in zip(normal, m['normal'])) > .999]
            face_info.append((face, state, masks))
            for triangle in triangles:
                points = [tuple(verts[i]) for i in triangle]
                lookup[key(points)] = (state, masks)
        angle = self.records[name]['rotated_x_degrees']
        mesh.transform(App.Placement(App.Vector(), App.Rotation(App.Vector(1, 0, 0), angle)).toMatrix())
        bb = mesh.BoundBox
        origin = App.Vector(bb.XMin, bb.YMin, bb.ZMin)
        self.cache[name] = lookup, origin, App.Rotation(App.Vector(1, 0, 0), -angle), face_info
        self.backgrounds[name] = max(areas, key=areas.get)
        return self.cache[name]

    def patch(self, source, target):
        with ZipFile(source) as z:
            data = {n: z.read(n) for n in z.namelist()}
        config = ET.fromstring(data['Metadata/model_settings.config'])
        names = {o.get('id'): next(m.get('value') for m in o.findall('metadata') if m.get('key') == 'name')
                 for o in config.findall('object')}
        root = ET.fromstring(data['3D/3dmodel.model'])
        statistics, used = [], set()
        for obj in root.findall('c:resources/c:object', NS):
            name = names[obj.get('id')].removesuffix('.stl')
            lookup, origin, inverse, face_info = self.part(name)
            object_config = next(o for o in config.findall('object') if o.get('id') == obj.get('id'))
            next(m for m in object_config.findall('metadata') if m.get('key') == 'extruder').set('value', str(self.backgrounds[name]))
            counts, area_by_state = Counter(), defaultdict(float)
            for component in obj.findall('c:components/c:component', NS):
                path = component.get('{'+NS['p']+'}path').lstrip('/')
                model = ET.fromstring(data[path])
                mesh = next(o for o in model.findall('c:resources/c:object', NS)
                            if o.get('id') == component.get('objectid')).find('c:mesh', NS)
                verts = [[float(v.get(a)) for a in 'xyz'] for v in mesh.findall('c:vertices/c:vertex', NS)]
                verts = transform(verts, component.get('transform'))
                verts = [tuple(inverse.multVec(App.Vector(*p)+origin)) for p in verts]
                for triangle in mesh.findall('c:triangles/c:triangle', NS):
                    points = [verts[int(triangle.get(a))] for a in ('v1', 'v2', 'v3')]
                    triangle_key = key(points)
                    if triangle_key not in lookup:
                        # OCCT can retessellate a face when queried on its own.
                        # Classify these original STL triangles against the
                        # original CAD surfaces, within the mesh deflection.
                        center = App.Vector(*[sum(p[i] for p in points)/3 for i in range(3)])
                        probe = Part.Vertex(center)
                        candidates = []
                        for face, state, face_masks in face_info:
                            bb = face.BoundBox
                            if all(getattr(bb, a+'Min')-.025 <= center[i] <= getattr(bb, a+'Max')+.025
                                   for i, a in enumerate('XYZ')):
                                candidates.append((face.distToShape(probe)[0], state, face_masks))
                        candidates.sort(key=lambda item: item[0])
                        assert candidates and candidates[0][0] < .025, (name, center, candidates[:1])
                        _, base, masks = candidates[0]
                        lookup[triangle_key] = base, masks
                        counts['cad_surface_fallback_facets'] += 1
                    base, masks = lookup[triangle_key]
                    if masks:
                        axes = masks[0]['axes']
                        projected = [tuple(p[i] for i in axes) for p in points]
                        paint, areas = paint_triangle(projected, base, [(m['state'], m['polygon']) for m in masks])
                        for state, area in areas.items():
                            area_by_state[state] += area
                        used.update(areas)
                    else:
                        paint = leaf(base)
                        used.add(base)
                    triangle.set('paint_color', paint)
                    counts['painted_facets'] += 1
                    counts['split_facets'] += len(paint) > 2
                data[path] = ET.tostring(model, encoding='utf-8', xml_declaration=True)
            statistics.append(dict(part=name, base_filament=self.backgrounds[name], **counts, ribbon_face_area_mm2=dict(area_by_state)))
        data['Metadata/model_settings.config'] = ET.tostring(config, encoding='utf-8', xml_declaration=True)
        settings = json.loads(data['Metadata/project_settings.config'])
        settings['enable_prime_tower'] = '1' if len(used) > 1 else '0'
        data['Metadata/project_settings.config'] = json.dumps(settings, ensure_ascii=False, indent=2).encode()
        with ZipFile(target, 'x', ZIP_DEFLATED) as z:
            for path, raw in data.items():
                z.writestr(path, raw)
        return statistics, sorted(used)


def geometry_signatures(project):
    """Ignore plate arrangement and material data when comparing real meshes."""
    import hashlib
    with ZipFile(project) as z:
        config = ET.fromstring(z.read('Metadata/model_settings.config'))
        names = {o.get('id'): next(m.get('value') for m in o.findall('metadata') if m.get('key') == 'name')
                 for o in config.findall('object')}
        root = ET.fromstring(z.read('3D/3dmodel.model'))
        result = {}
        for obj in root.findall('c:resources/c:object', NS):
            triangles = []
            for component in obj.findall('c:components/c:component', NS):
                model = ET.fromstring(z.read(component.get('{'+NS['p']+'}path').lstrip('/')))
                mesh = next(o for o in model.findall('c:resources/c:object', NS)
                            if o.get('id') == component.get('objectid')).find('c:mesh', NS)
                verts = [[float(v.get(a)) for a in 'xyz'] for v in mesh.findall('c:vertices/c:vertex', NS)]
                verts = transform(verts, component.get('transform'))
                triangles.extend([verts[int(t.get(a))] for a in ('v1', 'v2', 'v3')]
                                 for t in mesh.findall('c:triangles/c:triangle', NS))
            # Bambu can move the component's translation into the build item
            # when saving. Compare meshes after removing only this translation.
            origin = [min(p[i] for t in triangles for p in t) for i in range(3)]
            triangles = [key([[p[i]-origin[i] for i in range(3)] for p in t]) for t in triangles]
            result[names[obj.get('id')]] = hashlib.sha256(json.dumps(sorted(triangles)).encode()).hexdigest()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--export-dir', required=True, type=Path)
    parser.add_argument('--single-color-dir', required=True, type=Path)
    parser.add_argument('--only', nargs='+')
    parser.add_argument('--output')
    args = parser.parse_args()
    args.export_dir = args.export_dir.resolve()
    args.single_color_dir = args.single_color_dir.resolve()
    geometry = verified_manifest(args.export_dir, 'geometry-export')
    single = verified_manifest(args.single_color_dir, 'print-projects')
    assert single['export_manifest_sha256'] == sha(args.export_dir/'manifest.json')
    plan = read_json(ROOT/'printing/plate-plan.json')
    plates_by_id = {p['id']:p for p in plan['plates']}
    assert single['plan_sha256'] == sha(ROOT/'printing/plate-plan.json')
    if args.only:
        assert set(args.only) <= {p['id'] for p in single['projects']}
    out = output_directory(args.output, 'multicolor')
    for folder in ('3mf', 'logs', 'profiles'):
        (out/folder).mkdir()
    profiles = []
    for name, hexcode in PALETTE:
        profile = read_json(PROFILES/'PLA-black.json')
        profile['filament_colour'] = [hexcode]
        path = out/'profiles'/f'PLA-{name}.json'
        write_json(path, profile)
        profiles.append(path)
    for supports in (False, True):
        process = read_json(PROFILES/('PLA-0.20-support-process.json' if supports else 'PLA-0.20-process.json'))
        process['enable_prime_tower'] = '1'
        write_json(out/'profiles'/f'process-support-{int(supports)}.json', process)
    before = sha(CAD)
    doc = App.openDocument(str(CAD))
    projects = []
    TMP.mkdir(parents=True, exist_ok=True)
    try:
        painter = CADPaint(doc, geometry)
        for record in single['projects']:
            plate_id = record['id']
            if args.only and plate_id not in args.only:
                continue
            print('Preparing colour', plate_id, flush=True)
            supports = record['settings']['enable_support'] == '1'
            process = read_json(PROFILES/('PLA-0.20-support-process.json' if supports else 'PLA-0.20-process.json'))
            process.update(plates_by_id[plate_id].get('process_overrides', {}))
            process['enable_prime_tower'] = '1'
            process_file = out/'profiles'/f'{plate_id}-process.json'
            write_json(process_file, process)
            project = out/'3mf'/f'{plate_id}-mpower.3mf'
            with tempfile.TemporaryDirectory(prefix='color-', dir=TMP) as temp:
                scratch = Path(temp)
                configured, painted = scratch/'configured.3mf', scratch/'painted.3mf'
                run_cli(['--load-settings', f'{PROFILES / "X2D-0.4-standard-machine.json"};{process_file}',
                         '--load-filaments', ';'.join(map(str, profiles)), '--orient', '0', '--arrange', '0',
                         '--export-3mf', configured,
                         *(args.export_dir / next(p['print_file'] for p in geometry['print_parts'] if p['part'] == name)
                           for name in record['parts'])],
                        scratch/'configure', out/'logs'/f'{plate_id}-configure.log')
                statistics, used = painter.patch(configured, painted)
                if plates_by_id[plate_id].get('color_mode') == 'single':
                    slots = dict(black=1,white=2,lightblue=3,darkblue=4,red=5)
                    assert used == [slots[plates_by_id[plate_id]['color']]], (plate_id,used)
                run_cli(['--orient', '0', '--arrange', '1', '--allow-multicolor-oneplate',
                         '--export-3mf', project, painted], scratch/'save', out/'logs'/f'{plate_id}-save.log')
                bounds = project_bounds(project)
                assert len(bounds) == len(record['parts'])
                signatures = geometry_signatures(project)
                assert signatures == geometry_signatures(args.single_color_dir/record['project']), plate_id
                with ZipFile(project) as z:
                    settings = json.loads(z.read('Metadata/project_settings.config'))
                    assert settings['filament_colour'] == [h for _, h in PALETTE]
                    assert settings['enable_prime_tower'] == ('1' if len(used) > 1 else '0')
                    for k,v in plates_by_id[plate_id].get('process_overrides', {}).items():
                        assert settings[k] == v, (plate_id,k,settings[k],v)
                    assert all('paint_color=' in z.read(n).decode() for n in z.namelist()
                               if n.startswith('3D/Objects/') and n.endswith('.model'))
                    persisted_states = set()
                    for n in z.namelist():
                        if n.startswith('3D/Objects/') and n.endswith('.model'):
                            for t in ET.fromstring(z.read(n)).findall('.//c:triangle', NS):
                                persisted_states.update(paint_states(t.get('paint_color')))
                    assert sorted(persisted_states) == used, (plate_id, persisted_states, used)
                    project.with_suffix('.png').write_bytes(z.read('Metadata/plate_1.png'))
                sliced = scratch/'sliced'
                sliced.mkdir()
                run_cli(['--orient', '0', '--arrange', '0', '--outputdir', sliced, '--slice', '0', project],
                        scratch/'reload', out/'logs'/f'{plate_id}-slice.log')
                result = read_json(sliced/'result.json')
                write_json(out/'logs'/f'{plate_id}-result.json', result)
                assert result['return_code'] == 0 and len(result['sliced_plates']) == 1, result
                saved = result['sliced_plates'][0]
                assert len(saved['objects']) == len(record['parts']) and not saved['warning_message'], saved
                actual = sorted(f['id'] for f in saved['filaments'] if f['total_used_g'] > .001)
                assert actual == used, (plate_id, actual, used)
            project_record = dict(id=plate_id, parts=record['parts'], project=str(project.relative_to(out)),
                                  project_sha256=sha(project), palette_slots_used=used,
                                  geometry_sha256_by_part=signatures, geometry_matches_single_color=True,
                                  facet_paint=statistics, object_bounds=bounds, settings=settings,
                                  saved_project_reopened_and_sliced=True, reload_profile_overrides=False,
                                  warning_messages=[], filament_changes=saved['filament_change_times'],
                                  estimated_seconds=saved['total_predication'],
                                  filaments=saved['filaments'],
                                  estimated_filament_g=sum(f['total_used_g'] for f in saved['filaments']))
            projects.append(project_record)
            write_json(out/'progress.json', projects)
            print('PASS colour', plate_id, 'slots', used, 'g', project_record['estimated_filament_g'], flush=True)
    finally:
        App.closeDocument(doc.Name)
    assert sha(CAD) == before
    manifest = dict(source_record(), kind='colored-print-projects', status='passed',
                    geometry_manifest_sha256=sha(args.export_dir/'manifest.json'),
                    single_color_manifest_sha256=sha(args.single_color_dir/'manifest.json'),
                    plan_sha256=sha(ROOT/'printing/plate-plan.json'), plan_status=plan['status'],
                    palette=[dict(slot=i+1, name=n, hex=h) for i, (n,h) in enumerate(PALETTE)],
                    complete_plan=len(projects) == len(plan['plates']), projects=projects,
                    ribbon_boundary_tolerance_mm=.20, geometry_modified=False,
                    physical_print_and_fit_tested=False, gcode_delivered=False)
    manifest['files'] = {str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()}
    write_json(out/'manifest.json', manifest)
    print('PASS', len(projects), 'coloured projects;', out, flush=True)


if __name__ == '__main__':
    main()
