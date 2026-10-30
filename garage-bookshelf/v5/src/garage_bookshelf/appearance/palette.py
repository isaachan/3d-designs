"""Current face palette restoration; no one-time upgrade or CAD writes."""
from collections import Counter
import FreeCAD as App
from garage_bookshelf.paths import ROOT
from garage_bookshelf.rendering.software import saved_colors
BACKUP = ROOT / 'archive/snapshots/2026-10-26-before-mpower-colors.FCStd'
HEX = dict(Black='#16181B', Recess='#0E1013', LightBlue='#39A9DB',
           DarkBlue='#151B65', Red='#ED242A', White='#F4F5F6', Hardware='#24272B')
RGB = {k: tuple(int(v[i:i+2], 16)/255 for i in (1, 3, 5)) for k, v in HEX.items()}


def face_palette(body, old):
    name = body.SourcePart
    faces = body.Shape.Faces
    old = old if len(old) == len(faces) else old*len(faces)
    colors = [RGB['Black']]*len(faces)
    if 'SkinColor' in body.PropertiesList:
        return [RGB[body.SkinColor]]*len(faces)
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
            obj.ViewObject.Visibility = doc.getObject('SkinParameters') is None or obj.SurfaceRole == 'Post'
            obj.ViewObject.Selectable = False
    if doc.getObject('SkinConstruction'):
        for obj in doc.SkinConstruction.Group:
            obj.ViewObject.Visibility = False
        doc.SkinConstruction.ViewObject.Visibility = False
        doc.SkinParameters.ViewObject.Visibility = False
    for obj in doc.Objects:
        if obj.TypeId == 'App::Origin':
            obj.ViewObject.Visibility = False
    return counts
