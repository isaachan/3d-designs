"""Regression checks against serialized 3MF files, not just in-memory meshes."""
from pathlib import Path
import hashlib, json, zipfile, xml.etree.ElementTree as E

ROOT=Path(__file__).resolve().parent/'generated'
NS={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}

def load(name):
    with zipfile.ZipFile(ROOT/name) as z:
        assert z.testzip() is None
        r=E.fromstring(z.read('3D/3dmodel.model'))
        c=E.fromstring(z.read('Metadata/model_settings.config'))
    objects={o.get('id'):o for o in r.findall('m:resources/m:object',NS)}
    assert len(c.findall('plate'))==6
    built={i.get('objectid') for i in r.findall('m:build/m:item',NS)}
    result={}
    for obj in c.findall('object'):
        oid=obj.get('id'); assert oid in built
        name=obj.find("metadata[@key='name']").get('value')
        references={s.get('objectid') for s in objects[oid].findall('m:components/m:component',NS)}
        assert references=={p.get('id') for p in obj.findall('part')}
        parts=[]
        for part in obj.findall('part'):
            mesh=objects[part.get('id')].find('m:mesh',NS)
            parts.append((part.find("metadata[@key='extruder']").get('value'),hashlib.sha256(E.tostring(mesh)).hexdigest()))
        result[name]=parts
    assert len(built)==12
    return result

bmw=load('BMW-Modular-V2-DRAFT.3mf')
blank=load('Brand-Template-V2-DRAFT.3mf')
common={name:parts for name,parts in bmw.items() if name.startswith('Universal')}
assert len(common)==7  # road + shell + five stops
for name,parts in common.items(): assert blank[name]==parts,name
report={'six_plates_in_both_projects':True,'twelve_built_objects_in_each':True,'component_references_valid':True,'universal_objects_identical':list(common),'mesh_sha256':common}
(ROOT/'export-validation.json').write_text(json.dumps(report,indent=2))
print('Serialized 3MF checks passed: 6 plates, 12 objects, 7 identical universal objects.')
