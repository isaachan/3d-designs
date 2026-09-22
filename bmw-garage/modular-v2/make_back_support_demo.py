"""Small white demo of the front-fascia rear support ledge."""
from pathlib import Path
import json, zipfile, xml.etree.ElementTree as E
import numpy as np
import trimesh as tm
import generate as g

OUT = Path(__file__).resolve().parent / 'generated' / 'temp-fit-review'
OUT.mkdir(parents=True, exist_ok=True)
g.COLORS = {1: '#FFFFFF'}
g.NAMES = ['TEMP - Back support ledge demo']

entries = []
checks = []
CENTER = (128, 128)
GAP = 0.20


def add(name, mesh, xy):
    parts = g.normalized({1: mesh}, g.IDENTITY)
    b = tm.util.concatenate(list(parts.values())).bounds
    assert np.all(b[0, :2] + xy >= -115) and np.all(b[1, :2] + xy <= 115), (name, b, xy)
    for m in parts.values():
        assert m.is_watertight and m.is_volume, name
    checks.append({'name': name, 'bounds_mm': b.tolist(), 'bed_xy_offset': xy})
    entries.append((name, parts, 1, (CENTER[0] + xy[0], CENTER[1] + xy[1], 0)))


def peg_print(cx):
    # Printed like the real sign: face panel is flat on the bed, pegs grow upward.
    # A tiny stepped lead-in is enough for this visual/mechanical demo.
    base = g.block(cx - 4, cx + 4, -2, 2, 2.4, 6.5)
    lead = g.block(cx - 3.3, cx + 3.3, -1.65, 1.65, 6.5, 7.4)
    return g.union([base, lead])


# Short removable fascia: 70 x 16 x 2.4 with two standard 8 x 4 pegs.
sign_panel = g.block(-35, 35, -8, 8, 0, 2.4)
sign = g.union([sign_panel, peg_print(-24), peg_print(24)])

# Receiver printed front-face-up for easy observation: the raised continuous strip is
# the support ledge. Two square pockets match the pegs with 0.20 mm per-side gap.
base = g.block(-39, 39, -11, 11, 0, 3.0)
ledge = g.block(-36, 36, -8.8, 8.8, 3.0, 5.4)
# Relief windows around the peg holes keep the ledge visibly interrupted at sockets.
receiver = g.union([base, ledge])
pockets = []
for cx in [-24, 24]:
    pockets.append(g.block(cx - 4 - GAP, cx + 4 + GAP, -2 - GAP, 2 + GAP, 2.35, 5.8))
    # A bevel-like lead-in pocket shows why the peg can find the hole.
    pockets.append(g.block(cx - 5.2, cx + 5.2, -3.2, 3.2, 5.35, 5.9))
receiver = g.diff(receiver, pockets)

# A thin loose cross-section slice shows the side view of sign-back, peg, and ledge.
# It is not a functional connector; it is a teaching cutaway. Keep it self-supporting
# for printing: the base/ledge extend under the whole sign strip so there is no
# long cantilever that would trigger support generation.
cut_base = g.block(-24, 18, -4, 4, 0, 3.0)
cut_ledge = g.block(-24, 18, -4, 4, 3.0, 5.4)
cut_sign = g.block(-24, 14, -4, 4, 5.4, 7.8)
cut_peg = g.block(-4, 4, -3, 3, 3.0, 5.4)
cutaway = g.union([cut_base, cut_ledge, cut_sign, cut_peg])

add('short removable sign with two pegs - white', sign, (-45, 30))
add('short receiver with continuous back support ledge - white', receiver, (-45, -20))
add('one-piece side cutaway showing ledge contact - white', cutaway, (45, 0))

path = OUT / 'Back-Support-Ledge-Demo-TEMP.3mf'
g.project(path, entries)

ns = {'m': g.CORE}
with zipfile.ZipFile(path) as z:
    assert z.testzip() is None
    root = E.fromstring(z.read('3D/3dmodel.model'))
    meshes = 0
    for obj in root.findall('m:resources/m:object', ns):
        mesh = obj.find('m:mesh', ns)
        if mesh is None:
            continue
        vs = [[float(v.get(k)) for k in ('x', 'y', 'z')] for v in mesh.findall('m:vertices/m:vertex', ns)]
        fs = [[int(t.get(k)) for k in ('v1', 'v2', 'v3')] for t in mesh.findall('m:triangles/m:triangle', ns)]
        m = tm.Trimesh(vertices=vs, faces=fs, process=False)
        assert m.is_watertight and m.is_volume
        meshes += 1

(OUT / 'back-support-demo-validation.json').write_text(json.dumps({
    'status': 'TEMP white demo; not a final production interface',
    'file': str(path),
    'objects': len(entries),
    'exported_meshes_checked': meshes,
    'socket_clearance_each_side_mm': GAP,
    'note': 'Receiver is printed front-face-up to make the support ledge visible. It demonstrates the ledge concept, not final full-length dimensions.',
    'parts': checks,
}, indent=2))
print(path)
print(f'Validated {len(entries)} objects, {meshes} meshes')
