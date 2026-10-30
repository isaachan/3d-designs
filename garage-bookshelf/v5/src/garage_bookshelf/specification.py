"""Roles are explicit: appearance, hardware and samples are not print parts."""
import json
from garage_bookshelf.paths import ROOT

CENTRES = [('ColumnInset', 'ColumnInset'), ('ColumnX2', 'ColumnInset'),
           ('ColumnInset', 'ColumnY2'), ('ColumnX2', 'ColumnY2')]


def specification():
    return json.loads((ROOT / 'cad/model-spec.json').read_text())


def role(body):
    name = body.SourcePart
    spec = specification()
    if name in spec['print_parts']:
        return 'print'
    if name in spec['hardware']:
        return 'hardware'
    if name in spec['samples']:
        return 'sample'
    raise ValueError(f'Unclassified Body: {body.Name}; update cad/model-spec.json')


def bodies(doc, roles=('print', 'hardware')):
    return [o for o in doc.Objects if o.TypeId == 'PartDesign::Body' and role(o) in roles]


def appearance_graphics(doc):
    separate = doc.getObject('SkinParameters') is not None
    return [o for o in doc.Objects if 'MColor' in o.PropertiesList
            and (not separate or o.SurfaceRole == 'Post')]
