# Frozen v4 source; use v5/tools or the migrated studies.
if __name__ == '__main__':
    raise SystemExit('Historical entry disabled; see v5/README.md and archive/README.md')

"""Approved M Power appearance, applied incrementally to the formal v4 CAD.

Run ``import apply_mpower_colors as m; m.run()`` in FreeCAD's Python console.
Existing solid features are never edited. Native, fully constrained sketches,
face binders and face/face Commons describe editable, zero-thickness graphics.
No Python Feature proxies, meshes, textures or external image dependencies.
"""
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import FreeCAD as App
import Part
from assembly import global_shape
from geometry.sketches import loops
from render_parking_recesses import saved_colors

CAD = ROOT / 'garage-bookshelf-v4-assembly.FCStd'
BACKUP = ROOT / 'backups/2026-10-26-before-mpower-colors.FCStd'
CANDIDATE = ROOT / 'previews/mpower-colors/mpower-candidate.FCStd'
REPORT = ROOT / 'reports/mpower-color-validation.json'
EXPECTED_SHA256 = '953a522b4d01374917c4059389e7691d33765f07aa986b8fe3a7561fea6dbcbe'

HEX = dict(Black='#16181B', Recess='#0E1013', LightBlue='#39A9DB',
           DarkBlue='#151B65', Red='#ED242A', White='#F4F5F6', Hardware='#24272B')
RGB = {k: tuple(int(v[i:i+2], 16)/255 for i in (1, 3, 5)) for k, v in HEX.items()}
MP = 'MColorParameters.'
DP = 'DesignParameters.'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def print_files():
    return {str(p.relative_to(ROOT)): sha(p) for p in ROOT.rglob('*')
            if p.is_file() and p.suffix.lower() in ('.step', '.stl', '.3mf', '.zip')}


def bbox(shape):
    b = shape.BoundBox
    return [b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax]


def original_bodies(doc):
    return {b.Name: dict(shape=b.Shape.copy(), global_shape=global_shape(b),
                         tip=b.Tip.Name, placement=str(b.getGlobalPlacement()),
                         brep=hashlib.sha256(b.Shape.exportBrepToString().encode()).hexdigest())
            for b in doc.Objects if b.TypeId == 'PartDesign::Body'}


def sketch(group, name, polygons, **kwargs):
    # The existing sketch builder qualifies bare design aliases itself.
    clean = lambda value: str(value).replace(DP, '')
    polygons = [[(clean(x), clean(y)) for x, y in poly] for poly in polygons]
    if 'offset' in kwargs:
        kwargs['offset'] = tuple(clean(v) for v in kwargs['offset'])
    return loops(group, name, polygons, **kwargs)


def parameters(doc, parent):
    sheet = doc.addObject('Spreadsheet::Sheet', 'MColorParameters')
    sheet.Label = 'M Power 配色参数 · 三色共用宽度'
    parent.addObject(sheet)
    rows = [
        ('StripeWidth', '36 mm', '三色统一实际宽度；垂直于带方向测量'),
        ('Slope', '0.6', '背板 dx/dz；底板镜像衔接，保持各面实际等宽'),
        ('Pitch', '=StripeWidth*sqrt(1+Slope^2)', '同一横截线上每条色带的截距宽度'),
        ('Right', '=DesignParameters.OverallWidth-DesignParameters.WallThickness', '背板顶边三色右界'),
        ('CornerLeft', '=Right-Slope*(DesignParameters.OverallHeight-DesignParameters.BaseThickness)-3*Pitch', '背板与底板折线处三色左界'),
        ('DisplayOffset', '0.01 mm', '仅零厚度外观面显示避闪偏移；不是材料厚度'),
    ]
    for col, value in zip('ABC', ['Alias', 'Value', '说明']):
        sheet.set(col+'1', value)
    for row, (alias, value, note) in enumerate(rows, 2):
        sheet.set('A'+str(row), alias)
        sheet.set('B'+str(row), value)
        sheet.setAlias('B'+str(row), alias)
        sheet.set('C'+str(row), note)
    for col, width in [('A', 160), ('B', 290), ('C', 460)]:
        sheet.setColumnWidth(col, width)
    sheet.set('A10', 'Palette HEX (sRGB)')
    for row, (key, value) in enumerate(HEX.items(), 11):
        sheet.set('A'+str(row), key)
        sheet.set('B'+str(row), value)
    doc.recompute()
    return sheet


def skin(doc, group, name, body_names, axis, coordinate, normal):
    support = []
    for name_body in body_names:
        b = doc.getObject(name_body)
        shape = global_shape(b)
        selected = []
        for i, face in enumerate(shape.Faces, 1):
            bb = face.BoundBox
            if (abs(getattr(bb, axis+'Min')-coordinate) < 1e-6 and
                    abs(getattr(bb, axis+'Max')-coordinate) < 1e-6 and
                    face.normalAt(0, 0).dot(App.Vector(*normal)) > .999):
                selected.append('Face'+str(i))
        if selected:
            # Refer through the owning assembly container so FreeCAD includes
            # its placement, rather than binding Body-local faces at the origin.
            support.append((doc.getObject(b.SourcePart), [b.Name+'.'+s for s in selected]))
    assert support, name
    refs = []
    for source, names in support:
        for sub in names:
            b = doc.addObject('PartDesign::SubShapeBinder', 'M_FaceRef_'+name)
            group.addObject(b)
            b.Support = [(source, [sub])]
            b.Relative = True
            b.MakeFace = False
            refs.append(b)
    doc.recompute()
    if len(refs) > 1:
        # OCCT can misclassify coplanar faces in a raw compound at the F joint.
        # A native face union resolves their boundaries before color clipping.
        b = doc.addObject('Part::MultiFuse', 'M_Skin_'+name)
        group.addObject(b)
        b.Shapes = refs
        b.Refine = True
        doc.recompute()
    else:
        b = refs[0]
    b.Label = name+' · 原主体表面引用（隐藏）'
    assert len(b.Shape.Faces) > 0, (name, b.State)
    # References must be in assembly coordinates, not module-local coordinates.
    assert abs(getattr(b.Shape.BoundBox, axis+'Min')-coordinate) < 1e-6
    assert abs(getattr(b.Shape.BoundBox, axis+'Max')-coordinate) < 1e-6
    return b


def face_graphic(doc, group, name, color, profile, surface, normal):
    face = doc.addObject('PartDesign::SubShapeBinder', 'M_Profile_'+name)
    group.addObject(face)
    face.Support = [(profile, [])]
    face.MakeFace = True
    doc.recompute()
    assert len(face.Shape.Faces) == 1, (name, face.State)
    clipped = doc.addObject('Part::Common', 'M_Paint_'+name)
    group.addObject(clipped)
    clipped.Label = name+' · 零厚度外观色面'
    clipped.Base = face
    clipped.Tool = surface
    doc.recompute()
    assert not clipped.Shape.isNull() and clipped.Shape.Area > .01, (name, clipped.State)
    assert len(clipped.Shape.Solids) == 0 and abs(clipped.Shape.Volume) < 1e-8
    for kind, prop, val in [('App::PropertyString', 'MColor', color),
                            ('App::PropertyString', 'AppearanceOnly', 'Zero-thickness paint map; exclude from solid/STL exports.'),
                            ('App::PropertyString', 'SurfaceRole', name.rsplit('_', 1)[0])]:
        clipped.addProperty(kind, prop, 'M Power appearance')
        setattr(clipped, prop, val)
    clipped.addProperty('App::PropertyVector', 'DisplayNormal', 'M Power appearance')
    clipped.DisplayNormal = App.Vector(*normal)
    for axis, value in zip('xyz', normal):
        if value:
            clipped.setExpression('Placement.Base.'+axis, f'{value}*{MP}DisplayOffset')
    doc.recompute()
    return clipped


def make_graphics(doc):
    assert doc.getObject('MPowerAppearance') is None, 'Appearance already installed; use refresh_colors().'
    parent = doc.addObject('App::Part', 'MPowerAppearance')
    parent.Label = 'M Power 配色 · 可编辑外观面（非打印实体）'
    parent.addProperty('App::PropertyString', 'Purpose', 'M Power appearance')
    parent.Purpose = 'Approved black concept. Exact 1:1:1 stripe widths. Solid geometry unchanged.'
    helpers = doc.addObject('App::DocumentObjectGroup', 'M_Construction')
    helpers.Label = '外观构造草图与表面引用（隐藏）'
    parent.addObject(helpers)
    parameters(doc, parent)
    books = ['module_2_Body', 'module_3_Body']
    value = lambda alias: float(doc.DesignParameters.evalExpression(DP+alias).Value)
    back, base, top = value('BackFront'), value('BaseThickness'), value('OverallHeight')
    surfaces = {
        'Back': skin(doc, helpers, 'Back', books, 'Y', back, (0, -1, 0)),
        'BackJoint': skin(doc, helpers, 'BackJoint', books, 'Y', back-value('Overlap'), (0, -1, 0)),
        'Floor': skin(doc, helpers, 'Floor', books, 'Z', base, (0, 0, 1)),
        'TopRim': skin(doc, helpers, 'TopRim', books, 'Z', top, (0, 0, 1)),
        'FrontEdge': skin(doc, helpers, 'FrontEdge', books, 'Y', 0, (0, -1, 0)),
        'Post': skin(doc, helpers, 'Post', ['billboard_Body'], 'Y', value('BillboardY'), (0, -1, 0)),
    }
    # All x boundaries use the same pitch. The perpendicular width on both
    # principal faces is pitch/sqrt(1+slope**2), exactly StripeWidth.
    for i, color in enumerate(('LightBlue', 'DarkBlue', 'Red')):
        left = f'{MP}CornerLeft+{i}*{MP}Pitch'
        right = f'{MP}CornerLeft+{i+1}*{MP}Pitch'
        B, T, Y, S = DP+'BaseThickness', DP+'OverallHeight', DP+'BackFront', MP+'Slope'
        specifications = [
            ('Back', 'XZ', ('0 mm', Y, '0 mm'),
             [(left, B), (right, B), (f'{right}+{S}*({T}-{B})', T), (f'{left}+{S}*({T}-{B})', T)], (0, -1, 0)),
            ('BackJoint', 'XZ', ('0 mm', Y+'-'+DP+'Overlap', '0 mm'),
             [(left, B), (right, B), (f'{right}+{S}*({T}-{B})', T), (f'{left}+{S}*({T}-{B})', T)], (0, -1, 0)),
            ('Floor', 'XY', ('0 mm', '0 mm', B),
             [(f'{left}+{S}*{Y}', '0 mm'), (f'{right}+{S}*{Y}', '0 mm'), (right, Y), (left, Y)], (0, 0, 1)),
            ('TopRim', 'XY', ('0 mm', '0 mm', T),
             [(f'{left}+{S}*({T}-{B})', Y), (f'{right}+{S}*({T}-{B})', Y),
              (f'{right}+{S}*({T}-{B})+{S}*{DP}BackThickness', DP+'BackRear'),
              (f'{left}+{S}*({T}-{B})+{S}*{DP}BackThickness', DP+'BackRear')], (0, 0, 1)),
            ('FrontEdge', 'XZ', ('0 mm', '0 mm', '0 mm'),
             [(f'{left}+{S}*({Y}-{B})', '0 mm'), (f'{right}+{S}*({Y}-{B})', '0 mm'),
              (f'{right}+{S}*{Y}', B), (f'{left}+{S}*{Y}', B)], (0, -1, 0)),
        ]
        for name, orient, offset, polygon, normal in specifications:
            label = name+'_'+color
            profile = sketch(helpers, 'M_Sketch_'+label, [polygon], orientation=orient, offset=offset)
            profile.Label = label+' · 等宽参数草图'
            face_graphic(doc, parent, label, color, profile, surfaces[name], normal)
    for i, color in ((1, 'LightBlue'), (2, 'Red')):
        x = DP+'PostX'+str(i)
        polygon = [(x, DP+'PostBottom'), (x+'+'+DP+'PostWidth', DP+'PostBottom'),
                   (x+'+'+DP+'PostWidth', DP+'BillboardBottom'), (x, DP+'BillboardBottom')]
        profile = sketch(helpers, 'M_Sketch_Post'+str(i), [polygon], orientation='XZ',
                        offset=('0 mm', DP+'BillboardY', '0 mm'))
        face_graphic(doc, parent, 'Post_'+str(i), color, profile, surfaces['Post'], (0, -1, 0))
    doc.recompute()
    return parent


def face_palette(body, old):
    name = body.SourcePart
    faces = body.Shape.Faces
    old = old if len(old) == len(faces) else old*len(faces)
    colors = [RGB['Black']]*len(faces)
    if name.startswith('hardware_'):
        return [RGB['Hardware']]*len(faces)
    if name in ('side_cartridge',):
        return [RGB['White'] if min(rgb) > .9 else RGB['DarkBlue'] for rgb in old]
    if name == 'top_carrier':
        return [RGB['White'] if f.BoundBox.YMin < -1.400001 else RGB['Black'] for f in faces]
    if 'ParkingBays' in body.PropertiesList:
        for i, (face, rgb) in enumerate(zip(faces, old)):
            if min(rgb) > .9:
                colors[i] = RGB['White']
            elif rgb[0] > .9 and rgb[1] > .6 and rgb[2] < .3:
                bb = face.BoundBox
                colors[i] = RGB['White' if bb.YLength < 1.1 and bb.XLength > 5 else 'LightBlue']
            elif rgb[0] < .3 and .3 < rgb[1] < .6 and rgb[2] > .6:
                colors[i] = RGB['DarkBlue']
            elif .55 < rgb[0] < .62:
                colors[i] = RGB['Recess']
        if name.startswith('garage_deck_'):
            color = ('LightBlue', 'DarkBlue', 'Red')[int(name[-1])-1]
            bb = body.Shape.BoundBox
            for i, face in enumerate(faces):
                b = face.BoundBox
                exterior = (b.XMax < 3.001 or b.XMin > bb.XMax-3.001 or
                            b.YMax < 3.001 or b.YMin > bb.YMax-3.001)
                if exterior and abs(b.ZLength-bb.ZLength) < 1e-6:
                    colors[i] = RGB[color]
    return colors


def refresh_colors(doc, source_colors=None):
    """Restore this scheme without rebuilding graphics or touching solids."""
    assert App.GuiUp, 'Run appearance assignment in the FreeCAD GUI.'
    source_colors = source_colors or saved_colors(BACKUP)
    counts = {}
    for obj in doc.Objects:
        if obj.TypeId == 'App::Part':
            obj.ViewObject.Visibility = obj.Name != 'ParkingTraySamples'
        if obj.TypeId != 'PartDesign::Body':
            continue
        for child in obj.Group:
            child.ViewObject.Visibility = False
        old = source_colors.get(obj.Tip.Name, source_colors.get(obj.Name, [RGB['Black']]))
        colors = face_palette(obj, old)
        for target in (obj, obj.Tip):
            target.ViewObject.ShapeColor = RGB['Black']
            target.ViewObject.DiffuseColor = colors
            target.ViewObject.LineColor = (.035, .035, .04)
            # Shaded mode leaves the narrow engraved paint visible; black
            # wire outlines would cover much of a sub-millimetre color fill.
            target.ViewObject.DisplayMode = 'Shaded'
            target.ViewObject.LineWidth = 1.0
            target.ViewObject.Visibility = obj.SourcePart != 'parking_tray_interface'
        counts[obj.Name] = dict(Counter(next(k for k, v in RGB.items() if v == rgb) for rgb in colors))
    for obj in doc.M_Construction.Group:
        obj.ViewObject.Visibility = False
    doc.M_Construction.ViewObject.Visibility = False
    doc.MColorParameters.ViewObject.Visibility = False
    for obj in doc.Objects:
        if 'MColor' in obj.PropertiesList:
            obj.ViewObject.ShapeColor = RGB[obj.MColor]
            obj.ViewObject.DiffuseColor = [RGB[obj.MColor]]*len(obj.Shape.Faces)
            # Match the substrate draw mode: Flat Lines applies a polygon
            # depth offset that can bury a zero-thickness face behind Shaded.
            obj.ViewObject.DisplayMode = 'Shaded'
            obj.ViewObject.LineColor = RGB[obj.MColor]
            obj.ViewObject.LineWidth = 1.0
            obj.ViewObject.Visibility = True
            obj.ViewObject.Selectable = False
    for obj in doc.Objects:
        if obj.TypeId == 'App::Origin':
            obj.ViewObject.Visibility = False
    return counts


def review(doc):
    """Save a readable front-left CAD view without rebuilding any geometry."""
    import FreeCADGui as Gui
    from gui_review import settle_view
    counts = refresh_colors(doc)
    doc.Label = 'garage-bookshelf v4 · M Power 黑色等宽三色'
    toward = App.Vector(-1.1, -2.4, 1.45)
    toward.normalize()
    right = App.Vector(0, 0, 1).cross(toward)
    right.normalize()
    up = toward.cross(right)
    view = Gui.activeDocument().activeView()
    view.setCameraOrientation(App.Rotation(right, up, toward, 'ZXY').Q)
    view.fitAll()
    settle_view()
    doc.save()
    view.saveImage(str(ROOT/'reports/mpower-freecad-preview.png'), 2000, 1350, 'White')
    if REPORT.exists():
        data = json.loads(REPORT.read_text())
        data.update(after_sha256=sha(CAD), source_body_face_color_counts=counts,
                    gui_preview='mpower-freecad-preview.png', saved_front_left_camera=True)
        REPORT.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
    print('PASS saved M Power GUI view and actual FreeCAD preview.', flush=True)
    return doc


def check(doc, originals):
    checked = []
    for name, before in originals.items():
        b = doc.getObject(name)
        assert b.Tip.Name == before['tip'], name
        assert str(b.getGlobalPlacement()) == before['placement'], name
        assert b.Shape.isValid() and len(b.Shape.Solids) == 1, name
        digest = hashlib.sha256(b.Shape.exportBrepToString().encode()).hexdigest()
        if digest != before['brep']:
            delta = b.Shape.cut(before['shape']).Volume+before['shape'].cut(b.Shape).Volume
            assert delta < 1e-7, (name, delta)
        assert abs(b.Shape.Volume-before['shape'].Volume) < 1e-7, name
        assert len(b.Shape.Faces) == len(before['shape'].Faces), name
        checked.append(dict(body=name, solid_unchanged=True, brep_identical=digest == before['brep']))
    assert len([b for b in doc.Objects if b.TypeId == 'PartDesign::Body']) == len(originals)
    params = doc.MColorParameters
    width = params.evalExpression(MP+'StripeWidth').Value
    slope = float(params.evalExpression(MP+'Slope'))
    pitch = params.evalExpression(MP+'Pitch').Value
    assert abs(pitch/math.sqrt(1+slope*slope)-width) < 1e-9
    sketches = [o for o in doc.Objects if o.Name.startswith('M_Sketch_')]
    assert all(s.FullyConstrained and 'Invalid' not in s.State for s in sketches)
    measurements = []
    for face_name in ('Back', 'BackJoint', 'Floor', 'TopRim', 'FrontEdge'):
        for color in ('LightBlue', 'DarkBlue', 'Red'):
            s = doc.getObject('M_Sketch_'+face_name+'_'+color)
            # The first edge crosses the ribbon at a common surface coordinate.
            actual = s.Geometry[0].length()/math.sqrt(1+slope*slope)
            assert abs(actual-width) < 1e-8, (s.Name, actual)
            a = s.Geometry[3].StartPoint-s.Geometry[3].EndPoint
            b = s.Geometry[1].EndPoint-s.Geometry[1].StartPoint
            assert a.cross(b).Length < 1e-6
            measurements.append(dict(surface=face_name, color=color, perpendicular_width_mm=actual))
    graphics = [o for o in doc.Objects if 'MColor' in o.PropertiesList]
    for o in graphics:
        assert not o.Shape.isNull() and o.Shape.isValid(), o.Name
        assert len(o.Shape.Solids) == 0 and abs(o.Shape.Volume) < 1e-8, o.Name
        if o.Name.startswith(('M_Paint_Back_', 'M_Paint_Floor_')):
            assert o.Shape.Area > .95*o.Base.Shape.Area, (o.Name, o.Shape.Area, o.Base.Shape.Area)
    assert len(graphics) == 17
    assert not any(o.Name.startswith('M_Paint_SideSign_') for o in doc.Objects)
    # Adjacent graphic regions may share edges, never overlap in area.
    overlaps = []
    for name in ('Back', 'Floor', 'TopRim', 'FrontEdge'):
        shapes = [doc.getObject('M_Paint_'+name+'_'+c).Shape for c in ('LightBlue', 'DarkBlue', 'Red')]
        for a, b in zip(shapes, shapes[1:]):
            area = a.common(b).Area
            assert area < 1e-7, (name, area)
            overlaps.append(dict(surface=name, overlap_area_mm2=area))
    return dict(original_body_count=len(originals), original_bodies=checked,
                original_solid_envelope_preserved=True,
                common_width_mm=width, stripe_width_ratio=[1, 1, 1],
                stripe_measurements=measurements, fully_constrained_new_sketches=len(sketches),
                native_appearance_faces=len(graphics), added_solid_volume_mm3=0,
                display_offset_mm=.01, display_offset_is_material_thickness=False,
                color_region_overlap_checks=overlaps)


def run():
    assert App.GuiUp, 'Run in the FreeCAD Python console.'
    import FreeCADGui as Gui
    assert sha(CAD) == EXPECTED_SHA256, 'Formal CAD changed; inspect before applying.'
    assert not any(Path(d.FileName) == CAD for d in App.listDocuments().values() if d.FileName), 'Close formal CAD first.'
    BACKUP.parent.mkdir(exist_ok=True)
    if BACKUP.exists():
        assert sha(BACKUP) == EXPECTED_SHA256
    else:
        shutil.copy2(CAD, BACKUP)
    print_before = print_files()
    doc = App.openDocument(str(CAD))
    doc.Label = 'garage-bookshelf v4 · M Power 黑色等宽三色'
    originals = original_bodies(doc)
    source_colors = saved_colors(CAD)
    make_graphics(doc)
    counts = refresh_colors(doc, source_colors)
    doc.recompute()
    result = check(doc, originals)
    Gui.Selection.clearSelection()
    view = Gui.activeDocument().activeView()
    view.viewAxonometric()
    view.fitAll()
    Gui.updateGui()
    CANDIDATE.parent.mkdir(parents=True, exist_ok=True)
    doc.saveAs(str(CANDIDATE))
    name = doc.Name
    App.closeDocument(name)
    doc = App.openDocument(str(CANDIDATE))
    reopened = check(doc, originals)
    # The saved materials must survive a normal open, without running this script.
    saved = saved_colors(CANDIDATE)
    for obj in doc.Objects:
        if 'MColor' in obj.PropertiesList:
            assert all(max(abs(a-b) for a, b in zip(rgb, RGB[obj.MColor])) < 1/255 for rgb in saved[obj.Name]), obj.Name
            assert obj.ViewObject.Visibility
    assert len(saved['garage_deck_1_Body']) == len(doc.garage_deck_1_Body.Shape.Faces)
    assert sha(CAD) == EXPECTED_SHA256
    doc.saveAs(str(CAD))
    assert print_files() == print_before
    result.update(status='passed', date='2026-10-26', formal_cad=str(CAD), backup=str(BACKUP),
                  before_sha256=EXPECTED_SHA256, after_sha256=sha(CAD), palette_hex=HEX,
                  source_body_face_color_counts=counts, normal_reopen_checks=reopened,
                  native_colors_survive_reopen=True, print_files_unchanged=True,
                  top_billboard_tricolor=False, side_sign_tricolor=False, posts=['LightBlue', 'Red'],
                  deck_edges_bottom_to_top=['LightBlue', 'DarkBlue', 'Red'],
                  reference_concept='/Users/kai.han/.codex/generated_images/01a173a3-7f0f-72b3-92ae-f0a463f27429/exec-4a596b6e-88dc-4a66-a695-16c6108dbd09.png')
    REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    review(doc)
    print('PASS M Power colors: formal CAD saved, solids unchanged, three 36 mm stripes.', flush=True)
    return doc


if __name__ == '__main__':
    run()
