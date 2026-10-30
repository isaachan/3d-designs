"""Adopt the approved separate-skin design, preserving the previous CAD snapshot."""
import argparse, copy, shutil, struct
from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED
import _bootstrap
import FreeCAD as App
from garage_bookshelf.paths import CAD, ROOT, output_directory, sha, write_json
from garage_bookshelf.skins import install
from garage_bookshelf.assembly import global_shape
from garage_bookshelf.appearance.palette import HEX
from garage_bookshelf.appearance.storage import material_records, serialize_material_records


def saved_views(source, candidate, doc, skins, extra_colors=None):
    with ZipFile(source) as z:
        old = {n:z.read(n) for n in z.namelist()}
    with ZipFile(candidate) as z:
        data = {n:z.read(n) for n in z.namelist()}
    tree = ET.fromstring(old['GuiDocument.xml'])
    group = tree.find('ViewProviderData')
    names = {obj.Name for obj in doc.Objects}
    for view in list(group):
        if view.get('name') not in names:
            group.remove(view)
    providers = {v.get('name'):v for v in group}
    def prop(v, name):
        return next(p for p in v.iter('Property') if p.get('name') == name)
    shape_template = providers['M_Paint_Back_LightBlue']
    type_templates = {'App::Part':'garage_deck_1',
                      'App::DocumentObjectGroup':'M_Construction',
                      'Spreadsheet::Sheet':'MColorParameters',
                      'PartDesign::Body':'module_2_Body'}
    original_names = set(providers)
    original_types = {}
    for obj in doc.Objects:
        if obj.Name in original_names:
            original_types.setdefault(obj.TypeId, obj.Name)
    for obj in doc.Objects:
        if obj.Name in providers:
            continue
        template_name = type_templates.get(obj.TypeId, original_types.get(obj.TypeId))
        template = providers[template_name] if template_name else shape_template
        view = copy.deepcopy(template)
        view.set('name', obj.Name); view.set('expanded', '0')
        prop(view,'Visibility')[0].set('value','false')
        group.append(view); providers[obj.Name] = view
    for name, raw in old.items():
        if name != 'GuiDocument.xml' and name not in data:
            data[name] = raw
    for obj in doc.Objects:
        if 'MColor' in obj.PropertiesList and obj.SurfaceRole != 'Post':
            prop(providers[obj.Name], 'Visibility')[0].set('value', 'false')
        if obj.TypeId == 'PartDesign::Body':
            for child in obj.Group:
                if child != obj.Tip:
                    prop(providers[child.Name], 'Visibility')[0].set('value', 'false')
    seed_file = prop(shape_template,'ShapeAppearance')[0].get('file')
    seed = material_records(old[seed_file])[0]
    targets = [(body, body.SkinColor) for body in skins]
    targets += [(doc.getObject(name+'_Body'), color) for name, color in (extra_colors or {}).items()]
    for body, color in targets:
        rgb = [int(HEX[color][i:i+2],16) for i in (1,3,5)]
        record = bytearray(seed)
        struct.pack_into('<I', record, 4, (rgb[0]<<24)|(rgb[1]<<16)|(rgb[2]<<8)|255)
        file = body.SourcePart+'-appearance.bin'
        data[file] = serialize_material_records([bytes(record)]*len(body.Shape.Faces))
        for obj in (body, body.Tip):
            view = providers[obj.Name]
            prop(view,'ShapeAppearance')[0].set('file',file)
            prop(view,'Visibility')[0].set('value','true')
            prop(view,'DisplayMode')[0].set('value','1')
    prop(providers['BookColorSkins'],'Visibility')[0].set('value','true')
    group.set('Count',str(len(providers)))
    data['GuiDocument.xml'] = ET.tostring(tree,encoding='utf-8',xml_declaration=True)
    temp = candidate.with_suffix('.views.FCStd')
    with ZipFile(temp,'w',ZIP_DEFLATED) as z:
        for n, raw in data.items(): z.writestr(n,raw)
    temp.replace(candidate)
    with ZipFile(candidate) as z: assert z.testzip() is None


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output'); p.add_argument('--adopt', action='store_true')
    a=p.parse_args(); out=output_directory(a.output,'implement-skins')
    before=sha(CAD)
    doc=App.openDocument(str(CAD))
    old_shapes={b.SourcePart:global_shape(b) for b in doc.Objects if b.TypeId=='PartDesign::Body'}
    skins=install(doc)
    reference=ROOT/'printing/time-optimization-2026-10-30/geometry/geometry.json'
    previous={s['role']+'_'+s['color']:s for s in __import__('json').loads(reference.read_text())['skins']}
    comparisons=[]
    for b in skins:
        expected=previous[b.SkinRole+'_'+b.SkinColor]['volume_mm3']
        error=abs(b.Shape.Volume-expected)/expected
        assert error<1e-5,(b.Name,b.Shape.Volume,expected,error)
        comparisons.append(dict(part=b.SourcePart,volume_mm3=b.Shape.Volume,relative_volume_error=error))
    for name, old in old_shapes.items():
        new=global_shape(doc.getObject(name+'_Body'))
        assert abs(old.Volume-new.Volume)<1e-6,name
        assert old.isSame(new) or old.cut(new).Volume+new.cut(old).Volume<1e-5,name
    volumes={b.Name:b.Shape.Volume for b in skins}
    doc.SkinParameters.set('B2','0.8 mm');doc.recompute()
    assert all(b.Shape.Volume>volumes[b.Name] for b in skins)
    doc.SkinParameters.set('B2','0.6 mm');doc.recompute()
    assert all(abs(b.Shape.Volume-volumes[b.Name])<1e-5 for b in skins)
    assert not any(o.TypeId.endswith('Python') for o in skins)
    candidate=out/CAD.name;doc.saveAs(str(candidate))
    saved_views(CAD,candidate,doc,skins)
    App.closeDocument(doc.Name)
    assert sha(CAD)==before
    if a.adopt:
        backup=ROOT/'archive/snapshots/2026-10-30-before-separate-skins.FCStd'
        if not backup.exists():shutil.copy2(CAD,backup)
        assert sha(backup)==before
        shutil.copy2(candidate,CAD)
    write_json(out/'implementation.json',dict(status='passed',previous_cad_sha256=before,
      cad_sha256=sha(candidate),adopted=a.adopt,skin_count=12,original_bodies_unchanged=len(old_shapes),
      native_features=True,parametric_thickness_recompute_passed=True,skin_comparisons=comparisons))
    print('PASS',candidate,'adopted',a.adopt,flush=True)


if __name__=='__main__': main()
