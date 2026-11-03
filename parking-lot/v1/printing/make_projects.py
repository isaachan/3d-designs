#!/usr/bin/env python3
"""Create native Bambu multipart 3MFs and independently reopen/slice each one."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
sys.path.insert(0, '/Applications/FreeCAD.app/Contents/Resources/lib')
sys.path.insert(0, str(REPO/'garage-bookshelf/v5/src'))
import FreeCAD
import Mesh
from garage_bookshelf.printing.bambu import run_cli as _run_cli
from garage_bookshelf.printing.threemf import project_bounds
from garage_bookshelf.printing.paint import leaf

PROFILES = REPO/'garage-bookshelf/v5/assets/print-profiles'
COLORS = ['black', 'white', 'lightblue', 'darkblue', 'red']
HEX = ['#181C21', '#EDF2F5', '#26A6D6', '#1C2666', '#E3212B']
NS = 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
ET.register_namespace('', NS)


def sha(file):
    return hashlib.sha256(Path(file).read_bytes()).hexdigest()


def write_json(file, data):
    Path(file).write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')


def run_cli(args, datadir, log):
    try:
        return _run_cli(args, datadir, log)
    finally:
        if log.exists():
            log.write_text(log.read_text().rstrip()+'\n')


def q(name):
    return '{'+NS+'}'+name


def seed(file, parts, used):
    """A real multipart object per mechanical part; colours are solid volumes."""
    model = ET.Element(q('model'), unit='millimeter')
    resources = ET.SubElement(model, q('resources'))
    config = ET.Element('config')
    built = []
    oid = 1
    for part in parts:
        entries = []
        for vol in part['volumes']:
            mesh = Mesh.Mesh(str(ROOT/vol['file']))
            vertices, triangles = mesh.Topology
            obj = ET.SubElement(resources, q('object'), id=str(oid), type='model', name=part['name']+'_'+COLORS[vol['color']])
            geom = ET.SubElement(obj, q('mesh'))
            vs = ET.SubElement(geom, q('vertices'))
            for v in vertices:
                ET.SubElement(vs, q('vertex'), x=f'{v.x:.7f}', y=f'{v.y:.7f}', z=f'{v.z:.7f}')
            ts = ET.SubElement(geom, q('triangles'))
            for tri in triangles:
                ET.SubElement(ts, q('triangle'), v1=str(tri[0]), v2=str(tri[1]), v3=str(tri[2]))
            entries.append((oid, used.index(vol['color'])+1, len(triangles)))
            oid += 1
        assembly = ET.SubElement(resources, q('object'), id=str(oid), type='model', name=part['name'])
        components = ET.SubElement(assembly, q('components'))
        for volume_id, _, _ in entries:
            ET.SubElement(components, q('component'), objectid=str(volume_id))
        ob = ET.SubElement(config, 'object', id=str(oid))
        ET.SubElement(ob, 'metadata', key='name', value=part['name'])
        ET.SubElement(ob, 'metadata', key='extruder', value=str(entries[0][1]))
        for volume_id, extruder, count in entries:
            component = ET.SubElement(ob, 'part', id=str(volume_id), subtype='normal_part')
            ET.SubElement(component, 'metadata', key='name', value=part['name']+'_'+COLORS[used[extruder-1]])
            ET.SubElement(component, 'metadata', key='extruder', value=str(extruder))
            ET.SubElement(component, 'mesh_stat', face_count=str(count), edges_fixed='0', degenerate_facets='0',
                          facets_removed='0', facets_reversed='0', backwards_edges='0')
        built.append(oid)
        oid += 1
    build = ET.SubElement(model, q('build'))
    for top in built:
        ET.SubElement(build, q('item'), objectid=str(top))
    plate = ET.SubElement(config, 'plate')
    for key, value in [('plater_id', '1'), ('plater_name', 'Parking Lot'), ('locked', 'false'), ('filament_map_mode', 'Auto For Flush')]:
        ET.SubElement(plate, 'metadata', key=key, value=value)
    for index, top in enumerate(built):
        instance = ET.SubElement(plate, 'model_instance')
        for key, value in [('object_id', str(top)), ('instance_id', '0'), ('identify_id', str(index+1))]:
            ET.SubElement(instance, 'metadata', key=key, value=value)
    ET.SubElement(config, 'assemble')
    with ZipFile(file, 'w', ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
        z.writestr('_rels/.rels', '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
        z.writestr('3D/3dmodel.model', ET.tostring(model, encoding='utf-8', xml_declaration=True))
        z.writestr('Metadata/model_settings.config', ET.tostring(config, encoding='utf-8', xml_declaration=True))


def plan(parts):
    by = {p['name']: p for p in parts}
    plates = []

    def add(label, names, supports=None):
        pp = [by[n] for n in names]
        plates.append(dict(id=f'{len(plates):02d}-{label}', parts=names,
                           supports=any(p['supports'] for p in pp) if supports is None else supports))

    add('joint-fit-test', [p['name'] for p in parts if p['family']=='coupon'])
    for p in parts:
        if p['family'] in ('foundation', 'deck'):
            add(p['name'], [p['name']])
    for k in (1, 2, 3):
        for j in (1, 2, 3, 4):
            add(f'road-{k}-{j}', [f'road_{k}_{j}'])
    for k in (1, 2, 3, 4):
        add(f'landing-{k}F', [f'landing_{k}F'])
    add('all-original-columns', [p['name'] for p in parts if p['family']=='columns'])
    add('arms-feet-frame', [p['name'] for p in parts if p['family'] in ('arms-feet', 'sign-frame')])
    add('small-parts-pins-straps', [p['name'] for p in parts if p['family'] in ('small', 'pins')])
    add('back-wall', ['Garage_BackWall'])
    add('signs-and-labels', [p['name'] for p in parts if p['family']=='signs'])
    assigned = [name for plate in plates for name in plate['parts']]
    assert sorted(assigned) == sorted(by) and len(assigned)==len(set(assigned))
    return plates


def paint_volumes(source, target):
    """Persist Bambu facet states as well as volume filament assignments.

    X2D's automatic dual-nozzle assignment discovers used material states
    through facet paint. Volume extruder IDs alone leave its nozzle plan empty.
    """
    with ZipFile(source) as z:
        files = {n:z.read(n) for n in z.namelist()}
    cfg = ET.fromstring(files['Metadata/model_settings.config'])
    top = ET.fromstring(files['3D/3dmodel.model'])
    production = 'http://schemas.microsoft.com/3dmanufacturing/production/2015/06'
    ET.register_namespace('p', production)
    trees = {}
    for obj in cfg.findall('object'):
        default = next(int(m.get('value')) for m in obj.findall('metadata') if m.get('key')=='extruder')
        assignments = {p.get('id'):int(next((m.get('value') for m in p.findall('metadata') if m.get('key')=='extruder'), default)) for p in obj.findall('part')}
        model_obj = next(o for o in top.findall(q('resources')+'/'+q('object')) if o.get('id')==obj.get('id'))
        for component in model_obj.findall(q('components')+'/'+q('component')):
            path = component.get('{'+production+'}path').lstrip('/')
            if path not in trees:
                trees[path] = ET.fromstring(files[path])
            oid = component.get('objectid')
            volume = next(o for o in trees[path].findall(q('resources')+'/'+q('object')) if o.get('id')==oid)
            state = assignments[oid]
            for triangle in volume.findall('.//'+q('triangle')):
                triangle.set('paint_color', leaf(state))
    for path, tree in trees.items():
        files[path] = ET.tostring(tree, encoding='utf-8', xml_declaration=True)
    with ZipFile(target, 'w', ZIP_DEFLATED) as z:
        for path, raw in files.items():
            z.writestr(path, raw)


def make(plate, by):
    started = time.time()
    tag = plate['id']
    target = ROOT/'3mf'/f'{tag}.3mf'
    stats_file = ROOT/'results'/f'{tag}.json'
    selected = [by[n] for n in plate['parts']]
    used = sorted({v['color'] for p in selected for v in p['volumes']})
    process = json.loads((PROFILES/('PLA-0.20-support-process.json' if plate['supports'] else 'PLA-0.20-process.json')).read_text())
    process.update(layer_height='0.2', wall_loops='4', sparse_infill_density='25%',
                   wall_generator='arachne', enable_prime_tower='1' if len(used)>1 else '0',
                   prime_tower_width='30', brim_width='2' if any(p['family']=='road' for p in selected) else '4',
                   enable_support='1' if plate['supports'] else '0', support_on_build_plate_only='1',
                   support_interface_top_layers='3', support_interface_spacing='.25')
    if all(p['family'] in ('small', 'pins', 'coupon') for p in selected):
        process.update(sparse_infill_density='100%', sparse_infill_pattern='zig-zag', enable_prime_tower='0')
    process_file = ROOT/'profiles'/f'{tag}-process.json'
    write_json(process_file, process)
    filament_files = [ROOT/'profiles'/f'PLA-{COLORS[c]}.json' for c in used]
    with tempfile.TemporaryDirectory(prefix=tag+'-', dir=ROOT/'scratch') as temp:
        scratch = Path(temp)
        incoming = scratch/'input.3mf'
        seed(incoming, selected, used)
        run_cli(['--load-settings', f'{ROOT/"profiles/X2D-0.4-standard-machine.json"};{process_file}',
                 '--load-filaments', ';'.join(map(str, filament_files)),
                 '--orient', '0', '--arrange', '1', '--allow-multicolor-oneplate', '--allow-rotations',
                 '--export-3mf', target, incoming], scratch/'export-state', ROOT/'logs'/f'{tag}-export.log')
        if len(used)>1:
            painted = scratch/'painted.3mf'
            paint_volumes(target, painted)
            run_cli(['--orient', '0', '--arrange', '1', '--allow-multicolor-oneplate',
                     '--export-3mf', target, painted], scratch/'paint-state', ROOT/'logs'/f'{tag}-paint.log')
        with ZipFile(target) as z:
            cfg = ET.fromstring(z.read('Metadata/model_settings.config'))
            saved_plates = cfg.findall('plate')
            assert len(saved_plates)==1, (tag, 'arranged on multiple plates', len(saved_plates))
            settings = json.loads(z.read('Metadata/project_settings.config'))
            assert settings['printer_model']=='Bambu Lab X2D'
            assert settings['filament_colour']==[HEX[c] for c in used]
            assert len(cfg.findall('object'))==len(selected), (tag, 'mechanical object count')
            # Each original colour volume must remain an actual assigned part.
            saved_parts = [p for o in cfg.findall('object') for p in o.findall('part')]
            assert len(saved_parts)==sum(len(p['volumes']) for p in selected), (tag, 'colour volume count')
            assigned = set()
            for obj in cfg.findall('object'):
                default = next(int(m.get('value')) for m in obj.findall('metadata') if m.get('key')=='extruder')
                for component in obj.findall('part'):
                    values = {m.get('key'):m.get('value') for m in component.findall('metadata')}
                    extruder = int(values.get('extruder', default))
                    expected = used.index(COLORS.index(values['name'].rsplit('_', 1)[1]))+1
                    assert extruder==expected, (tag, values['name'], extruder, expected)
                    assigned.add(extruder)
            assert assigned==set(range(1, len(used)+1)), (tag, 'material mapping', assigned)
            target.with_suffix('.png').write_bytes(z.read('Metadata/plate_1.png'))
        bounds = project_bounds(target)
        assert len(bounds)==len(selected)
        sliced = scratch/'sliced'
        sliced.mkdir()
        run_cli(['--orient', '0', '--arrange', '0', '--outputdir', sliced, '--slice', '0', target],
                scratch/'reload-state', ROOT/'logs'/f'{tag}-slice.log')
        result = json.loads((sliced/'result.json').read_text())
        write_json(stats_file, result)
        assert result['return_code']==0
        assert len(result['sliced_plates'])==1
        record = result['sliced_plates'][0]
        assert len(record['objects'])==len(selected), (tag, 'sliced objects', record['objects'])
        assert not record['warning_message'], (tag, record['warning_message'])
        materials = []
        for f in record['filaments']:
            global_color = used[int(f['id'])-1]
            materials.append(dict(color=COLORS[global_color], grams=f['total_used_g'],
                                  main_grams=f.get('main_used_g'), local_filament_id=f['id']))
        summary = dict(**plate, project=str(target.relative_to(ROOT)), sha256=sha(target),
                       colors=[COLORS[c] for c in used], bounds=bounds, supports_enabled=plate['supports'],
                       saved_project_reopened_and_sliced=True, warning_message=record['warning_message'],
                       seconds=record['total_predication'], grams=sum(f['grams'] for f in materials),
                       materials=materials, filament_changes=record['filament_change_times'],
                       wall_loops=4, infill_density=process['sparse_infill_density'],
                       source_mesh_hashes={v['file']:sha(ROOT/v['file']) for p in selected for v in p['volumes']},
                       elapsed_generation_seconds=round(time.time()-started, 2))
        write_json(ROOT/'results'/f'{tag}-summary.json', summary)
        print('PASS', tag, round(summary['grams'], 1), 'g', round(summary['seconds']/3600, 2), 'h', flush=True)
        return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only', nargs='+')
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    data = json.loads((ROOT/'parts.json').read_text())
    for directory in ('3mf', 'results', 'profiles', 'scratch', 'logs'):
        (ROOT/directory).mkdir(exist_ok=True)
    for c, name in enumerate(COLORS):
        profile = json.loads((PROFILES/'PLA-black.json').read_text())
        profile['filament_colour'] = [HEX[c]]
        write_json(ROOT/'profiles'/f'PLA-{name}.json', profile)
    # Bundle the exact machine configuration used, rather than depending on
    # a profile silently changing in the other project later.
    (ROOT/'profiles/X2D-0.4-standard-machine.json').write_bytes((PROFILES/'X2D-0.4-standard-machine.json').read_bytes())
    plates = plan(data['parts'])
    write_json(ROOT/'plate-plan.json', dict(plates=plates, production_parts=len(data['parts'])-4, coupon_parts=4))
    by = {p['name']:p for p in data['parts']}
    for plate in plates:
        if args.only and plate['id'] not in args.only:
            continue
        existing = ROOT/'results'/f'{plate["id"]}-summary.json'
        if args.resume and existing.exists():
            old = json.loads(existing.read_text())
            if sha(ROOT/old['project']) == old['sha256'] and all(sha(ROOT/f)==s for f,s in old['source_mesh_hashes'].items()):
                print('REUSE', plate['id'], flush=True)
                continue
        print('Preparing', plate['id'], plate['parts'], flush=True)
        make(plate, by)


if __name__ == '__main__':
    main()
