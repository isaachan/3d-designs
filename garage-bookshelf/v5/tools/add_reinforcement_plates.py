"""Add the four glue-on plates to a checked candidate, optionally adopting it."""
import argparse
import shutil
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED

import _bootstrap
import FreeCAD as App
from garage_bookshelf.paths import CAD, ROOT, output_directory, sha, write_json
from garage_bookshelf.assembly import global_shape
from garage_bookshelf.reinforcement import install, check
from implement_separate_skins import saved_views


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output')
    parser.add_argument('--adopt', action='store_true')
    args = parser.parse_args()
    output = output_directory(args.output, 'reinforcement-cad')
    before = sha(CAD)
    doc = App.openDocument(str(CAD))
    old = {b.SourcePart: global_shape(b) for b in doc.Objects if b.TypeId == 'PartDesign::Body'}
    plates = install(doc)
    checks = check(doc)
    for name, original in old.items():
        current = global_shape(doc.getObject(name+'_Body'))
        assert abs(original.Volume-current.Volume) < 1e-6, name
        assert original.cut(current).Volume+current.cut(original).Volume < 1e-6, name
        assert max(abs(getattr(original.BoundBox, k)-getattr(current.BoundBox, k))
                   for k in ('XMin','YMin','ZMin','XMax','YMax','ZMax')) < 1e-6, name
    assert not [(o.Name, o.State) for o in doc.Objects if any(s in ('Invalid', 'Error') for s in o.State)]
    # Verify editable thickness affects all four native pads without changing their contact plane.
    doc.ReinforcementParameters.set('B4', '4 mm')
    doc.recompute(None, True, True)
    check(doc)
    assert all(abs(b.Shape.BoundBox.ZLength-4) < 1e-6 for b in plates)
    doc.ReinforcementParameters.set('B4', '3 mm')
    doc.recompute(None, True, True)
    check(doc)
    candidate = output/CAD.name
    doc.saveAs(str(candidate))
    saved_views(CAD, candidate, doc, [], {b.SourcePart: 'Black' for b in plates})
    with ZipFile(candidate) as archive:
        data = {name: archive.read(name) for name in archive.namelist()}
    tree = ET.fromstring(data['GuiDocument.xml'])
    visible = {'ReinforcementPlates'} | {b.getParentGeoFeatureGroup().Name for b in plates}
    for provider in tree.iter('ViewProvider'):
        if provider.get('name') in visible:
            prop = next(p for p in provider.iter('Property') if p.get('name') == 'Visibility')
            prop[0].set('value', 'true')
    data['GuiDocument.xml'] = ET.tostring(tree, encoding='utf-8', xml_declaration=True)
    temporary = candidate.with_suffix('.complete.FCStd')
    with ZipFile(temporary, 'w', ZIP_DEFLATED) as archive:
        for name, raw in data.items():
            archive.writestr(name, raw)
    temporary.replace(candidate)
    App.closeDocument(doc.Name)
    # Reopen the actual saved file, force full recompute, and check the installed plates again.
    doc = App.openDocument(str(candidate))
    doc.recompute(None, True, True)
    checks = check(doc)
    assert all(s.FullyConstrained for s in doc.Objects if s.TypeId == 'Sketcher::SketchObject')
    App.closeDocument(doc.Name)
    assert sha(CAD) == before
    if args.adopt:
        backup = ROOT/'archive/snapshots/2026-11-02-before-reinforcement-plates.FCStd'
        if not backup.exists():
            shutil.copy2(CAD, backup)
        assert sha(backup) == before
        shutil.copy2(candidate, CAD)
    write_json(output/'implementation.json', dict(status='passed', adopted=args.adopt,
        previous_cad_sha256=before, cad_sha256=sha(candidate),
        original_bodies_unchanged=len(old), plates=checks,
        fully_constrained_native_sketches=True, thickness_recompute_passed=True,
        saved_candidate_reopened_and_checked=True, physical_print_and_fit_tested=False))
    print('PASS', candidate, 'adopted', args.adopt, flush=True)


if __name__ == '__main__':
    main()
