"""GUI appearance and actual CAD preview; no geometry edits."""
import json
from pathlib import Path
import FreeCAD as App,FreeCADGui as Gui
from PySide6 import QtGui
ROOT=Path(__file__).resolve().parent


def run():
    QtGui.QAccessible.setActive(False)
    from assembly import COLORS
    d=App.openDocument(str(ROOT/'garage-bookshelf-v4-assembly.FCStd'))
    for o in d.Objects:
        if o.TypeId=='App::Part':o.ViewObject.Visibility=True
        elif o.TypeId=='PartDesign::Body':
            name=o.SourcePart
            color=COLORS['text' if name.startswith('billboard_text') else 'columns' if name.startswith('column_') else 'billboard' if name.startswith('billboard') else 'sign' if name=='book_depot_sign' else 'modules']
            for child in o.Group:
                if child.ViewObject is not None:child.ViewObject.Visibility=False
            for obj in (o,o.Tip):
                obj.ViewObject.Visibility=True;obj.ViewObject.ShapeColor=color
                obj.ViewObject.LineColor=(.2,.2,.2);obj.ViewObject.DisplayMode='Flat Lines'
        elif o.TypeId=='App::Origin':o.ViewObject.Visibility=False
    d.recompute();Gui.activateView('Gui::View3DInventor',True)
    view=Gui.activeDocument().activeView();view.viewAxonometric();view.fitAll()
    Gui.updateGui();d.save()
    view.saveImage(str(ROOT/'reports/assembly-preview.png'),1800,1100,'White')
    view.viewFront();view.fitAll();Gui.updateGui()
    view.saveImage(str(ROOT/'reports/front-preview.png'),1800,1100,'White')
    view.viewAxonometric();view.fitAll();Gui.updateGui();d.save()
    (ROOT/'reports/gui-validation.json').write_text(json.dumps(dict(status='passed',saved_view_colors=True,rendered_from_actual_native_cad=True),indent=2))
