# Frozen v4 source; use v5/tools or the migrated studies.
if __name__ == '__main__':
    raise SystemExit('Historical entry disabled; see v5/README.md and archive/README.md')

"""Read-only software previews of the updated native CAD's actual faces.

Uses the saved native view materials and an orthographic Z buffer. Does not
launch a GUI, edit geometry or regenerate any STEP/STL/3MF files.
"""
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, '/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as App
import numpy as np
from PIL import Image

from assembly import global_shape
from cad_view_style import material_records, diffuse_rgb


def saved_colors(file):
    with ZipFile(file) as z:
        root = ET.fromstring(z.read('GuiDocument.xml'))
        result = {}
        for vp in root.iter('ViewProvider'):
            prop = next((p for p in vp.iter('Property') if p.attrib.get('name') == 'ShapeAppearance'), None)
            if prop is not None:
                result[vp.attrib['name']] = [diffuse_rgb(r) for r in material_records(z.read(prop[0].attrib['file']))]
    return result


def triangles(doc, colors, names, local=False):
    points, paint = [], []
    light = np.array([-.45, -.65, .85])
    light /= np.linalg.norm(light)
    for name in names:
        body = doc.getObject(name+'_Body')
        shape = body.Shape.copy() if local else global_shape(body)
        base = colors.get(body.Tip.Name, colors.get(body.Name, [(.67, .70, .73)]))
        if len(base) != len(shape.Faces):
            base = [base[0]]*len(shape.Faces)
        for face, rgb in zip(shape.Faces, base):
            vertices, indices = face.tessellate(.12)
            if not indices:
                continue
            v = np.array([[p.x, p.y, p.z] for p in vertices])
            t = v[np.array(indices)]
            normal = np.cross(t[:, 1]-t[:, 0], t[:, 2]-t[:, 0])
            normal /= np.maximum(np.linalg.norm(normal, axis=1)[:, None], 1e-12)
            shade = .65+.35*np.abs(normal@light)
            points.extend(t)
            paint.extend(np.array(rgb)[None, :]*shade[:, None])
    return np.array(points), np.array(paint)


def render(points, paint, path, toward, width=1800, height=1200):
    toward = np.array(toward, dtype=float)
    toward /= np.linalg.norm(toward)
    right = np.cross([0., 0., 1.], toward)
    right /= np.linalg.norm(right)
    up = np.cross(toward, right)
    projected = points@np.stack([right, up, toward], axis=1)
    lo = projected.reshape(-1, 3).min(axis=0)
    hi = projected.reshape(-1, 3).max(axis=0)
    scale = min((width-120)/(hi[0]-lo[0]), (height-100)/(hi[1]-lo[1]))
    projected[:, :, 0] = (projected[:, :, 0]-(lo[0]+hi[0])/2)*scale+width/2
    projected[:, :, 1] = height/2-(projected[:, :, 1]-(lo[1]+hi[1])/2)*scale
    canvas = np.full((height, width, 3), 255, dtype=np.uint8)
    depth = np.full((height, width), -np.inf)
    for tri, rgb in zip(projected, paint):
        xmin, xmax = max(0, int(np.floor(tri[:, 0].min()))), min(width-1, int(np.ceil(tri[:, 0].max())))
        ymin, ymax = max(0, int(np.floor(tri[:, 1].min()))), min(height-1, int(np.ceil(tri[:, 1].max())))
        if xmax < xmin or ymax < ymin:
            continue
        x, y = np.meshgrid(np.arange(xmin, xmax+1)+.5, np.arange(ymin, ymax+1)+.5)
        a, b, c = tri
        den = (b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(den) < 1e-10:
            continue
        u = ((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/den
        v = ((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/den
        z = u*a[2]+v*b[2]+(1-u-v)*c[2]
        stored = depth[ymin:ymax+1, xmin:xmax+1]
        visible = (u >= -1e-8)&(v >= -1e-8)&(u+v <= 1+1e-8)&(z > stored)
        stored[visible] = z[visible]
        canvas[ymin:ymax+1, xmin:xmax+1][visible] = np.clip(rgb*255, 0, 255).astype(np.uint8)
    Image.fromarray(canvas).save(path)
    return dict(path=path.name, dimensions_px=[width, height], triangles=len(points),
                renderer='OpenCascade face tessellation and software Z buffer')


def main():
    file = ROOT/'garage-bookshelf-v4-assembly.FCStd'
    digest = hashlib.sha256(file.read_bytes()).hexdigest()
    doc = App.openDocument(str(file))
    colors = saved_colors(file)
    all_names = [b.SourcePart for b in doc.Objects
                 if b.TypeId == 'PartDesign::Body' and b.SourcePart != 'parking_tray_interface']
    garage_names = [n for n in all_names if n == 'module_1' or n.startswith(('garage_deck_', 'column_'))]
    records = []
    for name, objects, camera, local, width, height in [
        ('parking-recesses-assembly.png', all_names, [-1.2, -2.0, 1.25], False, 1800, 1200),
        ('parking-recesses-garage.png', garage_names, [-1.0, -2.8, 1.5], False, 1400, 1300),
        ('parking-recesses-deck-2.png', ['garage_deck_2'], [-1.0, -1.9, 2.8], True, 1500, 1100),
        ('parking-tray-interface.png', ['garage_deck_3', 'parking_tray_interface'], [-1.0, -2.4, 2.2], False, 1500, 1100),
    ]:
        p, rgb = triangles(doc, colors, objects, local)
        records.append(render(p, rgb, ROOT/'reports'/name, camera, width, height))
        print('RENDERED', name, flush=True)
    App.closeDocument(doc.Name)
    assert hashlib.sha256(file.read_bytes()).hexdigest() == digest
    (ROOT/'reports/parking-recesses-render-validation.json').write_text(json.dumps(
        dict(status='passed', cad_sha256=digest, native_geometry_only=True,
             saved_face_materials_used=True, cad_modified=False, previews=records), indent=2)+'\n')


if __name__ == '__main__':
    main()
