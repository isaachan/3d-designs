"""GUI viewing is separate from disk writes; save must be explicitly requested."""
from garage_bookshelf.paths import CAD


def settle_view():
    import FreeCADGui as Gui
    from PySide6 import QtCore
    loop = QtCore.QEventLoop()
    QtCore.QTimer.singleShot(900, loop.quit)
    loop.exec()
    Gui.updateGui()


def review(save=False):
    import FreeCAD as App
    import FreeCADGui as Gui
    from PySide6 import QtGui
    from pivy import coin  # registers the camera bindings
    from garage_bookshelf.appearance.palette import refresh_colors
    if not App.GuiUp:
        raise RuntimeError('Run review() inside the FreeCAD GUI')
    QtGui.QAccessible.setActive(False)
    doc = next((d for d in App.listDocuments().values() if d.FileName == str(CAD)), None)
    doc = doc or App.openDocument(str(CAD))
    refresh_colors(doc)
    toward = App.Vector(-1.1, -2.4, 1.45)
    toward.normalize()
    right = App.Vector(0, 0, 1).cross(toward)
    right.normalize()
    up = toward.cross(right)
    view = Gui.activeDocument().activeView()
    view.setCameraOrientation(App.Rotation(right, up, toward, 'ZXY').Q)
    view.fitAll()
    settle_view()
    if save:
        doc.save()
    return doc
