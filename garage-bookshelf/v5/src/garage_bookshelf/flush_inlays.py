"""Convert the external skins to flush, seated inlays using native CAD features."""
import FreeCAD as App
from garage_bookshelf.skins import COLORS, ROLES, part_name


def install(doc):
    if doc.getObject('book_skin_back_lightblue_SeatOutline'):
        raise ValueError('Flush inlays already installed')
    sheet = doc.SkinParameters
    sheet.set('B3', '0 mm')
    for row, (alias, value) in enumerate((('FitClearance', '0.15 mm'),
            ('SeatWidth', '1.5 mm'), ('GlueWellDepth', '0.2 mm')), 5):
        sheet.set('A'+str(row), alias)
        sheet.set('B'+str(row), value)
        sheet.setAlias('B'+str(row), alias)
    cores = [doc.module_2_Body, doc.module_3_Body]
    original_tips = {b.Name: b.Tip.Name for b in cores}
    # References must retain the original nominal surfaces after adding pockets.
    for obj in doc.Objects:
        if obj.TypeId != 'PartDesign::SubShapeBinder':
            continue
        pinned = []
        changed = False
        placement_source = None
        for support, subnames in obj.Support:
            names = []
            target = support
            for sub in subnames:
                for b in cores:
                    if sub.startswith(b.Name+'.'):
                        suffix = sub[len(b.Name)+1:]
                        if suffix.startswith(original_tips[b.Name]+'.'):
                            suffix = suffix[len(original_tips[b.Name])+1:]
                        target = doc.getObject(original_tips[b.Name])
                        sub = suffix
                        changed = True
                        placement_source = support
                names.append(sub)
            pinned.append((target, names))
        if changed:
            obj.Support = pinned
            obj.Placement = placement_source.getGlobalPlacement()
            for property_name, expression in placement_source.ExpressionEngine:
                if property_name.startswith('Placement.Base.'):
                    obj.setExpression(property_name, expression)
    doc.recompute()
    skins = []
    for color in COLORS:
        for role in ROLES:
            name = part_name(role, color)
            b = doc.getObject(name+'_Body')
            profile = doc.getObject(name+'_Profile')
            for axis, n in zip('xyz', b.SkinNormal):
                if n:
                    offset = '-SkinParameters.SkinThickness'
                    if role == 'TopRim':
                        offset += '-MColorParameters.DisplayOffset'
                    profile.setExpression('Placement.Base.'+axis, f'{n}*({offset})')
            if role == 'Floor':
                trim = doc.getObject(name+'_CornerTrim')
                trim.setExpression('Placement.Base.y', 'SkinParameters.SkinThickness+SkinParameters.CornerGap')
                trim.setExpression('Width',
                    'DesignParameters.BackFront-SkinParameters.SkinThickness-2*SkinParameters.CornerGap')
            if role == 'TopRim':
                trim = doc.addObject('Part::Box', name+'_CornerTrim')
                doc.SkinConstruction.addObject(trim)
                trim.Length = 2000; trim.Width = 1000; trim.Height = 2000
                trim.Placement.Base = App.Vector(-1000, 0, -1000)
                trim.setExpression('Placement.Base.y',
                    'DesignParameters.BackFront+SkinParameters.SkinThickness+SkinParameters.CornerGap')
                common = doc.addObject('Part::Common', name+'_TrimmedProfile')
                doc.SkinConstruction.addObject(common)
                common.Base = profile; common.Tool = trim; common.Refine = True
                doc.getObject(name+'_Extrusion').Base = common
            b.BaseFeature = doc.getObject(name+'_Extrusion')
            b.BaseFeature.DirMode = 'Custom'
            b.BaseFeature.Dir = b.SkinNormal
            doc.recompute()
            doc.removeObject(name+'_Relieved')
            doc.removeObject(name+'_JointClearance')
            b.Label = role+' · '+color+' · 齐平内嵌饰片'
            skins.append(b)
    doc.recompute()
    records = []
    construction = doc.SkinConstruction
    for skin in skins:
        name, normal = skin.SourcePart, skin.SkinNormal
        extrusion = doc.getObject(name+'_Extrusion')
        for kind, value, shift, depth in (
                ('Seat', 'SkinParameters.FitClearance',
                 'SkinParameters.SkinThickness+0.5 mm', 'SkinParameters.SkinThickness+0.5 mm'),
                ('GlueWell', '-SkinParameters.SeatWidth',
                 '0.02 mm', 'SkinParameters.GlueWellDepth+0.02 mm')):
            outline = doc.addObject('Part::Offset2D', name+'_'+kind+'Outline')
            construction.addObject(outline)
            outline.Source = extrusion.Base
            outline.setExpression('Value', value)
            outline.Fill = False
            doc.recompute()
            assert outline.Shape.isValid() and outline.Shape.Faces, outline.Name
            for core in cores:
                probe = outline.Shape.extrude(normal*-2)
                probe.Placement.Base += normal*1
                from garage_bookshelf.assembly import global_shape
                if probe.common(global_shape(core)).Volume < 1e-5:
                    continue
                prefix = core.SourcePart+'_'+skin.SkinRole+'_'+skin.SkinColor+'_'+kind
                profile = core.newObject('PartDesign::SubShapeBinder', prefix+'Profile')
                profile.Support = [(outline, ['Face'+str(i+1) for i in range(len(outline.Shape.Faces))])]
                profile.Relative = True; profile.MakeFace = True
                for axis, n in zip('xyz', normal):
                    if n:
                        profile.setExpression('Placement.Base.'+axis, f'{n}*({shift})')
                doc.recompute()
                previous = core.Shape.Volume
                pocket = core.newObject('PartDesign::Pocket', prefix+'Pocket')
                pocket.Profile = (profile, ['Face'+str(i+1) for i in range(len(profile.Shape.Faces))])
                pocket.AllowMultiFace = True
                pocket.Reversed = profile.Shape.Faces[0].normalAt(0, 0).dot(normal) < 0
                pocket.setExpression('Length', depth)
                pocket.Refine = True
                doc.recompute()
                assert pocket.Shape.isValid() and len(pocket.Shape.Solids) == 1, (pocket.Name, pocket.State)
                removed = previous-core.Shape.Volume
                assert removed > 1e-6, (pocket.Name, removed)
                records.append(dict(core=core.SourcePart, skin=name, kind=kind, removed_mm3=removed))
                print('Pocket', prefix, round(removed, 3), flush=True)
    doc.BookColorSkins.Label = '书架三色齐平嵌片 · 先拼主体再装饰片'
    doc.recompute()
    return skins, records
