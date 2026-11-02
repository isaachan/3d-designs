"""Four identical native pads bonded across the two rear module seams."""
import FreeCAD as App

from garage_bookshelf.assembly import global_shape, group, part
from garage_bookshelf.geometry.features import pad
from garage_bookshelf.geometry.sketches import rectangle
from garage_bookshelf.parameters import evaluate


PLATES = [
    ('reinforcement_garage_book_lower', '车库—左书架 · 下连接片',
     'GarageWidth', 'LowerBottom', ('module_1', 'module_2')),
    ('reinforcement_garage_book_upper', '车库—左书架 · 上连接片',
     'GarageWidth', 'UpperBottom', ('module_1', 'module_2')),
    ('reinforcement_book_book_lower', '左书架—右书架 · 下连接片',
     'GarageWidth+BookModuleWidth', 'LowerBottom', ('module_2', 'module_3')),
    ('reinforcement_book_book_upper', '左书架—右书架 · 上连接片',
     'GarageWidth+BookModuleWidth', 'UpperBottom', ('module_2', 'module_3')),
]


def install(doc):
    if doc.getObject('ReinforcementPlates'):
        raise ValueError('Reinforcement plates already installed; edit the parameter sheet instead')
    sheet = doc.addObject('Spreadsheet::Sheet', 'ReinforcementParameters')
    sheet.Label = '背面胶粘连接片参数（mm）'
    for col, text in zip('ABC', ('Alias', 'Value (mm)', '说明')):
        sheet.set(col+'1', text)
    values = [
        ('Width', '60 mm', '跨缝宽度；两侧各搭接30mm'),
        ('Height', '30 mm', '连接片高度'),
        ('Thickness', '3 mm', '连接片厚度'),
        ('LowerBottom', '18 mm', '下片底边高度；避开49mm起的燕尾接头'),
        ('TopMargin', '8 mm', '上片顶边到主体顶边的距离'),
        ('UpperBottom', '=DesignParameters.OverallHeight-Height-TopMargin', '上片底边随主体高度变化'),
    ]
    for row, (alias, value, note) in enumerate(values, 2):
        sheet.set(f'A{row}', alias)
        sheet.set(f'B{row}', value)
        sheet.setAlias(f'B{row}', alias)
        sheet.set(f'C{row}', note)
    sheet.setColumnWidth('A', 160)
    sheet.setColumnWidth('B', 240)
    sheet.setColumnWidth('C', 310)
    doc.recompute()
    parent = group(doc, 'ReinforcementPlates', '背面胶粘连接片 · 4件')
    result = []
    for name, label, seam, bottom, members in PLATES:
        container, body = part(doc, parent, name, label,
            position=(f'({seam})-ReinforcementParameters.Width/2',
                      'BackRear+ReinforcementParameters.Thickness',
                      f'ReinforcementParameters.{bottom}'),
            rotation=App.Rotation(App.Vector(1, 0, 0), 90))
        body.addProperty('App::PropertyBool', 'ReinforcementPlate', 'Manufacturing')
        body.ReinforcementPlate = True
        body.addProperty('App::PropertyStringList', 'JointMembers', 'Manufacturing')
        body.JointMembers = list(members)
        body.addProperty('App::PropertyString', 'Attachment', 'Manufacturing')
        body.Attachment = 'Rear adhesive bond; nominal contact, no holes or changes to existing parts'
        sketch = rectangle(body, name+'_Rectangle', 'ReinforcementParameters.Width',
                           'ReinforcementParameters.Height')
        pad(body, name+'_Pad', sketch, 'ReinforcementParameters.Thickness')
        result.append(body)
    doc.recompute(None, True, True)
    return result


def check(doc):
    """Check dimensions, rear contact on both members, and installed clearances."""
    rear = evaluate(doc, 'BackRear')
    report = []
    for name, _, seam, bottom, members in PLATES:
        body = doc.getObject(name+'_Body')
        assert body and body.ReinforcementPlate and body.Tip.TypeId == 'PartDesign::Pad', name
        assert body.Tip.Profile[0].FullyConstrained, name
        assert body.Shape.isValid() and len(body.Shape.Solids) == 1, name
        shape = global_shape(body)
        box = shape.BoundBox
        dimensions = [box.XLength, box.ZLength, box.YLength]
        expected = [doc.ReinforcementParameters.evalExpression(k).Value
                    for k in ('Width', 'Height', 'Thickness')]
        assert max(abs(a-b) for a, b in zip(dimensions, expected)) < 1e-6, name
        assert abs(box.YMin-rear) < 1e-6, name
        assert abs((box.XMin+box.XMax)/2-evaluate(doc, seam)) < 1e-6, name
        contact = next(f for f in shape.Faces if abs(f.CenterOfMass.y-rear) < 1e-6)
        areas = {member: contact.common(global_shape(doc.getObject(member+'_Body'))).Area
                 for member in members}
        nominal_side_area = expected[0]*expected[1]/2
        assert all(area >= nominal_side_area*.99 for area in areas.values()), (name, areas)
        overlaps = {}
        for other in doc.Objects:
            if other.TypeId != 'PartDesign::Body' or other == body:
                continue
            other_shape = global_shape(other)
            if box.intersect(other_shape.BoundBox):
                volume = shape.common(other_shape).Volume
                assert volume < .01, (name, other.Name, volume)
                overlaps[other.SourcePart] = volume
        report.append(dict(part=name, dimensions_width_height_thickness_mm=dimensions,
                           assembly_min_mm=[box.XMin, box.YMin, box.ZMin],
                           assembly_max_mm=[box.XMax, box.YMax, box.ZMax],
                           bond_area_mm2=areas, overlap_volumes_mm3=overlaps))
    return report
