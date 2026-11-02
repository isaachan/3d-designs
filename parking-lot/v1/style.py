"""Apply and save native FreeCAD GUI materials, visibility and camera."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent


def run():
    import FreeCAD as App
    import FreeCADGui as Gui
    from PySide6 import QtGui
    QtGui.QAccessible.setActive(False)
    path = ROOT/'cad/parking-lot-v1-assembly.FCStd'
    # Reopen this generated deliverable so a rebuild is reflected in the GUI.
    for existing in list(App.listDocuments().values()):
        if existing.FileName == str(path):
            App.closeDocument(existing.Name)
    doc = App.openDocument(str(path))
    for obj in doc.Objects:
        if obj.ViewObject is None:
            continue
        obj.ViewObject.Visibility = 'DeliveryVisible' in obj.PropertiesList and obj.DeliveryVisible
        if obj.TypeId == 'App::DocumentObjectGroup':
            obj.ViewObject.Visibility = obj.Name != 'Construction'
        if 'DesignColor' in obj.PropertiesList:
            obj.ViewObject.ShapeColor = tuple(obj.DesignColor[:3])
            obj.ViewObject.LineColor = (.04, .05, .06)
            obj.ViewObject.DisplayMode = 'Flat Lines' if obj.DesignRole in ('arm', 'post-base') else 'Shaded'
            obj.ViewObject.LineWidth = 1.
    # Body child objects occur after the body in the document and must be
    # revealed only after all construction objects have been hidden.
    for obj in doc.Objects:
        if obj.TypeId == 'PartDesign::Body' and obj.DeliveryVisible:
            obj.Tip.ViewObject.Visibility = True
            obj.Tip.ViewObject.ShapeColor = tuple(obj.DesignColor[:3])
            obj.Tip.ViewObject.DisplayMode = 'Shaded'
    App.setActiveDocument(doc.Name)
    Gui.activeDocument().activeView().viewAxonometric()
    # Match the concept's readable front-left perspective.
    toward = App.Vector(-.5, -.83, .5)
    toward.normalize()
    right = App.Vector(0, 0, 1).cross(toward)
    right.normalize()
    up = toward.cross(right)
    Gui.activeDocument().activeView().setCameraOrientation(App.Rotation(right, up, toward, 'ZXY').Q)
    Gui.activeDocument().activeView().fitAll()
    Gui.activeDocument().activeView().redraw()
    doc.recompute()
    doc.save()
    # GUI-aware STEP export retains colors and object names for other CAD apps.
    import Import
    objects = [o for o in doc.Objects if 'DeliveryVisible' in o.PropertiesList and o.DeliveryVisible]
    Import.export(objects, str(ROOT/'cad/parking-lot-v1-assembly.step'))
    Gui.activeDocument().activeView().saveImage(str(ROOT/'reports/freecad-gui-preview.png'), 1800, 1100, 'White')
    (ROOT/'reports/gui.json').write_text(json.dumps(dict(status='passed', gui_opened=True,
        colored_objects=len(objects), saved_native_appearance=True, colored_step_export=True), indent=2)+'\n')
    App.Console.PrintMessage('Parking Lot v1 appearance and STEP saved.\n')
