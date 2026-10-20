"""Run inside the FreeCAD GUI Python console to persist clean visibility and v2 colors."""
from pathlib import Path
import FreeCAD as App,FreeCADGui as Gui
ROOT=Path(__file__).resolve().parent

def appearance(doc):
    from assembly import COLORS
    from parameters import sync_count_metadata
    sync_count_metadata(doc)
    for o in doc.Objects:
        if o.TypeId=='App::Part':o.ViewObject.Visibility=True
        elif o.TypeId=='PartDesign::Body':
            name=o.SourcePart
            color=COLORS['text' if name.startswith('billboard_text') else 'columns' if name.startswith('garage_column') else 'billboard' if name.startswith('billboard') else 'sign' if name=='book_depot_sign' else 'modules']
            for child in o.Group:
                if child.ViewObject is not None:child.ViewObject.Visibility=False
            o.ViewObject.Visibility=True;o.ViewObject.ShapeColor=color
            o.Tip.ViewObject.Visibility=True;o.Tip.ViewObject.ShapeColor=color;o.Tip.ViewObject.LineColor=(.2,.2,.2);o.Tip.ViewObject.DisplayMode='Flat Lines'
        elif o.TypeId=='App::Origin':o.ViewObject.Visibility=False
    doc.recompute();Gui.activateView('Gui::View3DInventor',True);Gui.activeDocument().activeView().viewAxonometric();Gui.activeDocument().activeView().fitAll()

def open_model(which='assembly'):
    file=ROOT/f'garage-bookshelf-v3-{which}.FCStd'
    doc=App.openDocument(str(file));appearance(doc);doc.save();return doc
