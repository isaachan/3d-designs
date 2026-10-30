"""Native, editable colour skins; no Python feature proxies or imported meshes."""
import FreeCAD as App
from garage_bookshelf.assembly import global_shape

COLORS = ('LightBlue', 'DarkBlue', 'Red')
ROLES = ('Back', 'Floor', 'TopRim', 'FrontEdge')


def part_name(role, color):
    return 'book_skin_'+role.lower()+'_'+color.lower()


def install(doc):
    if doc.getObject('SkinParameters'):
        raise ValueError('Separate skins already installed')
    parent = doc.addObject('App::Part', 'BookColorSkins')
    parent.Label = '书架三色饰片 · 先拼主体再粘贴'
    construction = doc.addObject('App::DocumentObjectGroup', 'SkinConstruction')
    construction.Label = '饰片原生构造 · 隐藏'
    parent.addObject(construction)
    sheet = doc.addObject('Spreadsheet::Sheet', 'SkinParameters')
    parent.addObject(sheet)
    for row, (alias, value) in enumerate((('SkinThickness', '0.6 mm'),
            ('AdhesiveGap', '0.1 mm'), ('CornerGap', '0.1 mm')), 2):
        sheet.set('A'+str(row), alias)
        sheet.set('B'+str(row), value)
        sheet.setAlias('B'+str(row), alias)
    sheet.set('A1', 'Parameter'); sheet.set('B1', 'Value')
    sheet.setColumnWidth('A', 180); sheet.setColumnWidth('B', 120)
    frame = []
    for name in ('module_2', 'module_3'):
        binder = doc.addObject('PartDesign::SubShapeBinder', 'SkinFrame_'+name)
        construction.addObject(binder)
        binder.Support = [(doc.getObject(name), [name+'_Body.'])]
        binder.Relative = True; binder.MakeFace = False
        frame.append(binder)
    doc.recompute()
    for name, binder in zip(('module_2', 'module_3'), frame):
        assert abs(binder.Shape.Volume-global_shape(doc.getObject(name+'_Body')).Volume) < 1e-5
        assert abs(binder.Shape.BoundBox.XMin-global_shape(doc.getObject(name+'_Body')).BoundBox.XMin) < 1e-6
    made = []
    for color in COLORS:
        for role in ROLES:
            name = part_name(role, color)
            normal = App.Vector(0, -1, 0) if role in ('Back', 'FrontEdge') else App.Vector(0, 0, 1)
            graphic = doc.getObject('M_Paint_'+role+'_'+color)
            source = graphic.Base if role != 'TopRim' else graphic
            binder = doc.addObject('PartDesign::SubShapeBinder', name+'_Profile')
            construction.addObject(binder)
            binder.Support = [(source, ['Face1'])]
            binder.Relative = True; binder.MakeFace = True
            for axis, n in zip('xyz', normal):
                if n:
                    expression = 'SkinParameters.AdhesiveGap'
                    if role == 'TopRim':
                        expression += '-MColorParameters.DisplayOffset'
                    binder.setExpression('Placement.Base.'+axis, f'{n}*({expression})')
            base = binder
            if role == 'Floor':
                trim = doc.addObject('Part::Box', name+'_CornerTrim')
                construction.addObject(trim)
                trim.Length = 2000; trim.Height = 2000
                trim.Placement.Base = App.Vector(-1000, -1000, -1000)
                trim.setExpression('Width', 'DesignParameters.BackFront-SkinParameters.SkinThickness-SkinParameters.AdhesiveGap-SkinParameters.CornerGap+1000 mm')
                common = doc.addObject('Part::Common', name+'_TrimmedProfile')
                construction.addObject(common)
                common.Base = binder; common.Tool = trim; common.Refine = True
                base = common
            extrusion = doc.addObject('Part::Extrusion', name+'_Extrusion')
            construction.addObject(extrusion)
            extrusion.Base = base; extrusion.Dir = normal; extrusion.Solid = True
            extrusion.setExpression('LengthFwd', 'SkinParameters.SkinThickness')
            cutter = doc.addObject('Part::Compound', name+'_JointClearance')
            construction.addObject(cutter)
            cutter.Links = frame
            for axis, n in zip('xyz', normal):
                if n:
                    cutter.setExpression('Placement.Base.'+axis, f'{n}*SkinParameters.AdhesiveGap')
            cut = doc.addObject('Part::Cut', name+'_Relieved')
            construction.addObject(cut)
            cut.Base = extrusion; cut.Tool = cutter; cut.Refine = True
            body = doc.addObject('PartDesign::Body', name+'_Body')
            parent.addObject(body)
            body.Label = role+' · '+color+' · 可粘贴饰片'
            body.addProperty('App::PropertyString', 'SourcePart'); body.SourcePart = name
            body.addProperty('App::PropertyString', 'SkinColor'); body.SkinColor = color
            body.addProperty('App::PropertyString', 'SkinRole'); body.SkinRole = role
            body.addProperty('App::PropertyVector', 'SkinNormal'); body.SkinNormal = normal
            body.BaseFeature = cut
            made.append(body)
    doc.recompute()
    for b in made:
        assert b.Tip and b.Tip.TypeId == 'PartDesign::FeatureBase'
        assert b.Shape.isValid() and len(b.Shape.Solids) == 1, b.Name
    return made
