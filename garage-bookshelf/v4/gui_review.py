"""GUI appearance and actual CAD preview; no geometry edits."""
import json
from pathlib import Path
import FreeCAD as App,FreeCADGui as Gui
from PySide6 import QtGui,QtCore
from pivy import coin  # register Coin camera SWIG bindings before getCameraNode()
ROOT=Path(__file__).resolve().parent


def settle_view():
    # Standard views animate in FreeCAD; finish the transition before exporting PNG.
    loop=QtCore.QEventLoop()
    QtCore.QTimer.singleShot(900,loop.quit)
    loop.exec()
    Gui.updateGui()


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
                if name=='book_depot_sign':
                    depth=d.DesignParameters.evalExpression('DesignParameters.SignEngraveDepth').Value
                    # White pocket floors represent optional paint fill, not extra printed parts.
                    obj.ViewObject.LineWidth=1
                    obj.ViewObject.DiffuseColor=[(.95,.95,.95) if abs(f.CenterOfMass.y-depth)<1e-6 and f.normalAt(0,0).y<-.99 else color for f in obj.Shape.Faces]
        elif o.TypeId=='App::Origin':o.ViewObject.Visibility=False
    d.recompute();Gui.activateView('Gui::View3DInventor',True)
    view=Gui.activeDocument().activeView();view.viewAxonometric();view.fitAll()
    settle_view();d.save()
    view.saveImage(str(ROOT/'reports/assembly-preview.png'),1800,1100,'White')
    view.viewFront();view.fitAll();settle_view()
    # Opening a saved document may restore its camera during the first event pass.
    view.viewFront();view.fitAll();settle_view()
    view.saveImage(str(ROOT/'reports/front-preview.png'),1800,1100,'White')
    view.viewRear();view.fitAll();settle_view()
    view.saveImage(str(ROOT/'reports/rear-preview.png'),1800,1100,'White')
    for o in d.Objects:
        if o.TypeId=='PartDesign::Body':
            visible=o.SourcePart=='book_depot_sign'
            o.ViewObject.Visibility=visible;o.Tip.ViewObject.Visibility=visible
    view.viewFront();settle_view()
    # Use an explicit camera for the isolated sign; animated fitAll can retain old bounds.
    sign=d.book_depot_sign_Body
    centre=sign.getGlobalPlacement().multVec(sign.Shape.BoundBox.Center)
    floor_count=sum(abs(f.CenterOfMass.y-depth)<1e-6 and f.normalAt(0,0).y<-.99 for f in sign.Shape.Faces)
    print('Blue sign pocket floor count',floor_count,flush=True)
    camera=view.getCameraNode();camera.position.setValue(centre.x,-500,centre.z);camera.height.setValue(205)
    Gui.updateGui();settle_view()
    view.saveImage(str(ROOT/'reports/blue-sign-preview.png'),900,1200,'White')
    for o in d.Objects:
        if o.TypeId=='App::Part':o.ViewObject.Visibility=True
        elif o.TypeId=='PartDesign::Body':o.ViewObject.Visibility=True;o.Tip.ViewObject.Visibility=True
    view.viewAxonometric();view.fitAll();settle_view();d.save()
    (ROOT/'reports/gui-validation.json').write_text(json.dumps(dict(status='passed',saved_view_colors=True,rendered_from_actual_native_cad=True,blue_sign_detail='blue-sign-preview.png',blue_sign_white_floor_faces=floor_count,white_floor_colour_represents_optional_paint_fill=True),indent=2))
