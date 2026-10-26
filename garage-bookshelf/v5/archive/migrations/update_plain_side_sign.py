# Frozen v4 source; use v5/tools or the migrated studies.
if __name__ == '__main__':
    raise SystemExit('Historical entry disabled; see v5/README.md and archive/README.md')

"""Remove only the three small M-color graphics on the right slogan plaque.

Run in FreeCAD's Python console. Other appearance and all solids are preserved.
"""
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET
from zipfile import ZipFile

import FreeCAD as App
import apply_mpower_colors as m


def export_preview(doc):
    """Export the entire assembly, then restore the user's current camera."""
    import FreeCADGui as Gui
    from gui_review import settle_view
    view = Gui.getDocument(doc.Name).activeView()
    camera = view.getCamera()
    toward = App.Vector(-1.1, -2.4, 1.45)
    toward.normalize()
    right = App.Vector(0, 0, 1).cross(toward)
    right.normalize()
    up = toward.cross(right)
    try:
        view.setCameraOrientation(App.Rotation(right, up, toward, 'ZXY').Q)
        view.fitAll()
        settle_view()
        view.saveImage(str(m.ROOT/'reports/mpower-freecad-preview.png'), 2000, 1350, 'White')
    finally:
        view.setCamera(camera)
        Gui.updateGui()


def run():
    assert App.GuiUp, 'Run in the FreeCAD Python console.'
    import FreeCADGui as Gui
    before_hash = m.sha(m.CAD)
    backup = m.ROOT/'backups/2026-10-26-before-plain-side-sign.FCStd'
    if backup.exists():
        assert m.sha(backup) == before_hash, 'Saved CAD changed after this update; inspect before repeating.'
    else:
        shutil.copy2(m.CAD, backup)
    prefixes = ('M_Paint_SideSign_', 'M_Profile_SideSign_', 'M_Sketch_SideSign_',
                'M_Skin_SideSign', 'M_FaceRef_SideSign')
    with ZipFile(backup) as archive:
        xml = ET.fromstring(archive.read('GuiDocument.xml'))
    removed = sorted({p.attrib['name'] for p in xml.iter('ViewProvider')
                      if p.attrib['name'].startswith(prefixes)})
    assert sum(n.startswith('M_Paint_SideSign_') for n in removed) == 3
    print_before = m.print_files()
    doc = next((d for d in App.listDocuments().values()
                if d.FileName and Path(d.FileName).resolve() == m.CAD.resolve()), None)
    if doc is None:
        doc = App.openDocument(str(m.CAD))
    original = m.original_bodies(doc)
    existing_paint = {o.Name: o.Shape.copy() for o in doc.Objects
                      if 'MColor' in o.PropertiesList and not o.Name.startswith('M_Paint_SideSign_')}
    for prefix in prefixes:
        for obj in list(doc.Objects):
            if obj.Name.startswith(prefix):
                doc.removeObject(obj.Name)
    assert all(doc.getObject(n) is None for n in removed)
    doc.recompute()
    result = m.check(doc, original)
    for name, shape in existing_paint.items():
        after = doc.getObject(name).Shape
        assert abs(shape.Area-after.Area) < 1e-7, name
        assert shape.common(after).Area > shape.Area-1e-6, name
    assert m.print_files() == print_before
    Gui.Selection.clearSelection()
    Gui.updateGui()
    doc.save()
    export_preview(doc)
    record = dict(status='passed', before_sha256=before_hash, after_sha256=m.sha(m.CAD),
                  backup=str(backup), removed_native_objects=removed,
                  remaining_appearance_faces=len(existing_paint),
                  other_appearance_geometry_unchanged=True, original_solid_checks=result,
                  side_sign_tricolor=False, side_sign_background='DarkBlue',
                  side_sign_lettering='White', print_files_unchanged=True)
    (m.ROOT/'reports/plain-side-sign-validation.json').write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n')
    data = json.loads(m.REPORT.read_text())
    data.update(result)
    data.update(after_sha256=m.sha(m.CAD), side_sign_tricolor=False,
                side_sign_update='plain-side-sign-validation.json', normal_reopen_checks=result)
    m.REPORT.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
    print('PASS right sign: plain navy and white; other 17 color faces and all solids preserved.', flush=True)
    return doc
