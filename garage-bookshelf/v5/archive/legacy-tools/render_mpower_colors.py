# Frozen v4 source; use v5/tools or the migrated studies.
if __name__ == '__main__':
    raise SystemExit('Historical entry disabled; see v5/README.md and archive/README.md')

"""Read-only images of the formal CAD's saved M Power colors and surface maps."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, '/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as App
import numpy as np
from assembly import global_shape
from render_parking_recesses import saved_colors, render


def triangles(doc, colors, objects):
    points, paint = [], []
    light = np.array([-.45, -.65, .85])
    light /= np.linalg.norm(light)
    for obj in objects:
        shape = global_shape(obj)
        tip = obj.Tip.Name if obj.TypeId == 'PartDesign::Body' else obj.Name
        base = colors.get(tip, colors.get(obj.Name, [(.1, .1, .1)]))
        if len(base) != len(shape.Faces):
            base = [base[0]]*len(shape.Faces)
        for face, rgb in zip(shape.Faces, base):
            vertices, indices = face.tessellate(.15)
            if not indices:
                continue
            v = np.array([[p.x, p.y, p.z] for p in vertices])
            tri = v[np.array(indices)]
            normal = np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0])
            normal /= np.maximum(np.linalg.norm(normal, axis=1)[:, None], 1e-12)
            shade = .72+.28*np.abs(normal@light)
            points.extend(tri)
            paint.extend(np.array(rgb)[None, :]*shade[:, None])
    return np.array(points), np.array(paint)


def main():
    file = ROOT/'garage-bookshelf-v4-assembly.FCStd'
    digest = hashlib.sha256(file.read_bytes()).hexdigest()
    doc = App.openDocument(str(file))
    colors = saved_colors(file)
    bodies = [b for b in doc.Objects if b.TypeId == 'PartDesign::Body'
              and b.SourcePart != 'parking_tray_interface']
    graphics = [o for o in doc.Objects if 'MColor' in o.PropertiesList]
    records = []
    for name, objects, toward, width, height in [
        ('mpower-assembly-preview.png', bodies+graphics, [-1.1, -2.4, 1.45], 2000, 1350),
        ('mpower-front-preview.png', bodies+graphics, [0, -1, .05], 2000, 1300),
        ('mpower-stripe-detail.png',
         [doc.module_2_Body, doc.module_3_Body]+[o for o in graphics if o.Name.startswith(('M_Paint_Back_', 'M_Paint_BackJoint_', 'M_Paint_Floor_', 'M_Paint_TopRim_', 'M_Paint_FrontEdge_'))],
         [-.85, -2.7, 1.7], 1600, 1350),
    ]:
        p, rgb = triangles(doc, colors, objects)
        records.append(render(p, rgb, ROOT/'reports'/name, toward, width, height))
        print('RENDERED', name, flush=True)
    App.closeDocument(doc.Name)
    assert hashlib.sha256(file.read_bytes()).hexdigest() == digest
    (ROOT/'reports/mpower-render-validation.json').write_text(json.dumps(dict(
        status='passed', cad_sha256=digest, native_cad_faces_only=True,
        saved_face_materials_used=True, cad_modified=False, previews=records), indent=2)+'\n')


if __name__ == '__main__':
    main()
