"""Temporary P3/P4 fit experiment; does not modify the six-plate release."""
from pathlib import Path
import json
import zipfile
import xml.etree.ElementTree as E
import numpy as np
import trimesh as tm
import generate as g

OUT = Path(__file__).resolve().parent / 'generated' / 'temp-fit-review'
OUT.mkdir(parents=True, exist_ok=True)
g.build()
# Flush artwork does not change mating geometry. Merge its volumes into the
# backing so the test has no logo boundaries or separate color parts.
g.COLORS = {1: '#FFFFFF'}
g.NAMES = ['TEMP 1 - Clearance coupons', 'TEMP 2 - Full partition and fixture',
           'TEMP 3 - Full signs and receivers']
entries = []
# Bambu Studio lays three plates out in two columns (ceil(sqrt(3))).
# Plate 3 starts the second row, rather than continuing the six-plate grid.
centers = {1: (128, 128), 2: (435.2, 128), 3: (128, -179.2)}
checks = []


def add(name, parts, matrix, plate, xy):
    parts = g.normalized({1: g.union(list(parts.values()))}, matrix)
    bound = tm.util.concatenate(list(parts.values())).bounds
    lo, hi = bound[0, :2] + xy, bound[1, :2] + xy
    assert np.all(lo >= -122) and np.all(hi <= 122), (name, lo, hi)
    for prev in checks:
        if prev['plate'] == plate:
            a, b = np.array(prev['xy_bounds'])
            assert np.any(hi + 2 <= a) or np.any(b + 2 <= lo), (name, prev['name'])
    for mesh in parts.values():
        assert mesh.is_watertight and mesh.is_volume, name
    checks.append({'name': name, 'plate': plate, 'xy_bounds': [lo.tolist(), hi.tolist()],
                   'height_mm': float(bound[1, 2])})
    cx, cy = centers[plate]
    entries.append((name, parts, plate, (cx + xy[0], cy + xy[1], 0)))


# Same dimensions and orientations as the existing fit coupons. One common
# nominal male per column; the female clearance alone changes.
for i, gap in enumerate([.20, .30, .40]):
    rail = g.diff(g.block(0, 20, 0, 28, 0, 6),
                  [g.block(9-gap, 11+gap, -.1, 25, 3, 6.1)])
    panel = g.block(0, 20, 0, 12, 0, 2)
    socket = g.diff(g.block(0, 20, 0, 12, 0, 10),
                    [g.block(6-gap, 14+gap, -.1, 5.7, 3-gap, 7+gap)])
    socket = g.transform(socket, np.diag([1, -1, -1, 1]))
    pin = g.union([g.block(-8, 8, -6, 6, 0, 2.4),
                   g.transform(g.peg(0, 0, 2.4), np.linalg.inv(g.SIGN))])
    for j, (label, mesh) in enumerate([('rail', rail), ('panel', panel),
                                      ('socket', socket), ('peg', pin)]):
        add(f'{label} - gap {gap:.2f} per side', {3: mesh}, g.IDENTITY,
            1, (-65+i*65, -75+j*43))

# Crop the actual floor and shell around the left partition. The retained rear
# wall sets the actual roof height. Glue ONLY that wall onto the floor coupon;
# the partition and both channels remain glue-free.
floor = g.union(list(g.items[0]['parts'].values()))
shell = g.items[1]['parts'][3]
window = g.block(-38, -22, 18, 110, -1, 93)
floor_strip = tm.boolean.intersection([floor, window], engine='manifold')
shell_strip = tm.boolean.intersection([shell, window], engine='manifold')
add('P3 fixture FLOOR - rear edge Y110', {3: floor_strip}, g.IDENTITY, 2, (-96, 0))
add('P3 fixture ROOF plus REAR WALL - rear edge Y108', {3: shell_strip},
    g.items[1]['print_matrix'], 2, (-66, 0))
partition = next(it for it in g.items if it['plate'] == 3)
add('P3 plain full-size partition - gap 0.30 fixture', partition['parts'],
    partition['print_matrix'], 2, (12, 0))

# Receiver beams are cut from the real shell, preserving socket shape, spacing,
# surrounding wall thickness and roof-down printing orientation.
fascia_receiver = tm.boolean.intersection(
    [shell, g.block(-101, 101, 20, 29, 84, 92)], engine='manifold')
inner_receiver = tm.boolean.intersection(
    [shell, g.block(-23, 23, 99.5, 108, 39, 48)], engine='manifold')
signs = [it for it in g.items if it['plate'] == 4]
add('P4 actual 200mm fascia - 184mm peg spacing', signs[0]['parts'],
    signs[0]['print_matrix'], 3, (0, -78))
add('P4 fascia receiver beam - gap 0.30', {3: fascia_receiver},
    g.items[1]['print_matrix'], 3, (0, -47))
add('P4 actual interior sign - 32mm peg spacing', signs[1]['parts'],
    signs[1]['print_matrix'], 3, (-55, 12))
add('P4 interior receiver beam - gap 0.30', {3: inner_receiver},
    g.items[1]['print_matrix'], 3, (35, 12))

path = OUT / 'P3-P4-Fit-Review-TEMP.3mf'
g.project(path, entries)
# Check serialized object references and every exported mesh, not only originals.
ns = {'m': g.CORE}
with zipfile.ZipFile(path) as z:
    assert z.testzip() is None
    root = E.fromstring(z.read('3D/3dmodel.model'))
    config = E.fromstring(z.read('Metadata/model_settings.config'))
    objects = {o.get('id'): o for o in root.findall('m:resources/m:object', ns)}
    mesh_count = 0
    for obj in objects.values():
        mesh = obj.find('m:mesh', ns)
        if mesh is None:
            for component in obj.findall('m:components/m:component', ns):
                assert component.get('objectid') in objects
            continue
        vertices = [[float(v.get(k)) for k in ('x', 'y', 'z')]
                    for v in mesh.findall('m:vertices/m:vertex', ns)]
        faces = [[int(t.get(k)) for k in ('v1', 'v2', 'v3')]
                 for t in mesh.findall('m:triangles/m:triangle', ns)]
        m = tm.Trimesh(vertices=vertices, faces=faces, process=False)
        assert m.is_watertight and m.is_volume
        mesh_count += 1
    assert len(config.findall('plate')) == 3
    assert len(root.findall('m:build/m:item', ns)) == len(entries) == 19
(OUT / 'validation.json').write_text(json.dumps({
    'status': 'TEMP - not sliced or physically tested',
    'plates': 3, 'objects': len(entries), 'validated_exported_meshes': mesh_count,
    'mesh_volume_and_watertight_checks': True,
    'layout_bounds_and_2mm_separation_checks': True, 'parts': checks,
}, indent=2))
print(path)
print(f'Validated: 3 plates, {len(entries)} objects, {mesh_count} exported meshes')
