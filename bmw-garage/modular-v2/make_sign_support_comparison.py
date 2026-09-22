"""Create a view-only 3MF comparing the original fascia receiver and a rear-support version."""
from pathlib import Path
import json, zipfile, xml.etree.ElementTree as E
import numpy as np
import trimesh as tm
import generate as g

OUT = Path(__file__).resolve().parent / 'generated' / 'temp-fit-review'
OUT.mkdir(parents=True, exist_ok=True)

g.build()
g.COLORS = {1:'#16191D', 2:'#63A64B', 3:'#B7C5CE', 4:'#FFFFFF', 5:'#2B8FD3'}
g.NAMES = ['Original fascia interface - VIEW ONLY', 'With rear support ledge - VIEW ONLY']

shell = g.items[1]['parts'][3]
fascia_sign = next(it for it in g.items if it['name'] == 'BMW front fascia')

# Cut the real front receiver area from the shell: roof front edge and the two socket towers.
receiver_window = g.block(-103, 103, 19.6, 30.0, 83.8, 104.2)
original_receiver = tm.boolean.intersection([shell, receiver_window], engine='manifold')

# A continuous back-stop plane behind the sign face. It gives the long panel a datum to rest on.
# Socket clearances are cut back out so the pegs still pass through freely.
raw_ledge = g.block(-101.5, 101.5, 19.85, 21.35, 84.0, 104.0)
socket_cuts = [
    g.block(x-4-g.GAP, x+4+g.GAP, 19.75, 25.8, 85.65, 90.35)
    for x in [-92, 92]
]
rear_support_ledge = g.diff(raw_ledge, socket_cuts)
receiver_with_ledge = g.union([original_receiver, rear_support_ledge])

# Explode the sign 22 mm forward so the support face can be seen. Also keep a faint installed copy
# at nominal position for contact/alignment inspection.
exploded_sign = {5: g.move(g.union(list(fascia_sign['parts'].values())), (0, -22, 0))}
installed_sign = {4: g.move(g.union(list(fascia_sign['parts'].values())), (0, 0, 0))}

# Add small arrows/direction bars: blue bar marks insertion direction; red thin strip marks the former
# unsupported top half location on the original.
def arrow_bar(y):
    return g.union([
        g.block(-18, 18, y, y+1.4, 95, 96.4),
        g.block(14, 22, y-2.5, y+3.9, 94.4, 97.0),
    ])

entries = []
centers = {1:(128,128), 2:(435.2,128)}

def add_entry(name, parts, plate):
    parts = g.normalized(parts, g.IDENTITY)
    solid = tm.util.concatenate(list(parts.values()))
    b = solid.bounds
    assert np.all(b[0,:2] >= -125) and np.all(b[1,:2] <= 125), (name, b)
    assert all(m.is_watertight and m.is_volume for m in parts.values()), name
    entries.append((name, parts, plate, (*centers[plate], 0)))

add_entry('ORIGINAL - only two socket towers support the 200mm fascia', {
    3: original_receiver,
    5: exploded_sign[5],
    4: installed_sign[4],
    1: arrow_bar(-8),
}, 1)

add_entry('WITH REAR SUPPORT LEDGE - continuous back datum plus peg sockets', {
    3: original_receiver,
    2: rear_support_ledge,
    5: exploded_sign[5],
    4: installed_sign[4],
    1: arrow_bar(-8),
}, 2)

path = OUT / 'Sign-Back-Support-Comparison-VIEW-ONLY.3mf'
g.project(path, entries)

# Basic exported mesh validation.
ns = {'m': g.CORE}
with zipfile.ZipFile(path) as z:
    assert z.testzip() is None
    root = E.fromstring(z.read('3D/3dmodel.model'))
    config = E.fromstring(z.read('Metadata/model_settings.config'))
    assert len(config.findall('plate')) == 2
    meshes = 0
    for mesh_node in root.findall('.//m:mesh', ns):
        vertices = [[float(v.get(k)) for k in ('x','y','z')] for v in mesh_node.findall('m:vertices/m:vertex', ns)]
        faces = [[int(t.get(k)) for k in ('v1','v2','v3')] for t in mesh_node.findall('m:triangles/m:triangle', ns)]
        mesh = tm.Trimesh(vertices=vertices, faces=faces, process=False)
        assert mesh.is_watertight and mesh.is_volume
        meshes += 1
(OUT / 'sign-support-comparison-validation.json').write_text(json.dumps({
    'file': str(path),
    'status': 'VIEW ONLY - comparison of original vs rear support ledge',
    'plates': 2,
    'objects': len(entries),
    'exported_meshes_validated': meshes,
    'colors': {'gray':'existing receiver/shell', 'green':'new rear support ledge', 'blue':'exploded fascia', 'white':'installed fascia copy'},
    'nominal_fascia_back_face_y_mm': 20.0,
    'support_ledge_y_mm': [19.85, 21.35],
    'support_ledge_z_mm': [84.0, 104.0],
}, indent=2))
print(path)
