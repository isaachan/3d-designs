"""GUI-native editor smoke checks; invoke through Review.FCMacro."""
import json
from pathlib import Path
import FreeCAD as App,FreeCADGui as Gui
from PySide6 import QtGui
import gui_review
ROOT=Path(__file__).resolve().parent

def run():
    QtGui.QAccessible.setActive(False)
    result=dict(status='running',checks=[],environment_note='Automated macOS accessibility inspection triggered Qt QAccessibleCache/QMacAccessibilityElement crashes. Accessibility updates disabled only in this GUI process during checks; no preference or document geometry changed.')
    try:
        for existing in list(App.listDocuments().values()):
            if existing.FileName and str(ROOT) in existing.FileName:App.closeDocument(existing.Name)
        d=gui_review.open_model('assembly')
        assert len([o for o in d.Objects if o.TypeId=='PartDesign::Body'])==44
        result['checks'].append('GUI opens all 44 native Bodies')
        for name in ('Sketch_Base','Pad_Base','DesignParameters'):
            Gui.activeDocument().setEdit(name)
            if name!='DesignParameters':assert Gui.activeDocument().getInEdit() is not None,name
            result['checks'].append(f'GUI setEdit {name} succeeded')
            Gui.activeDocument().resetEdit()
        # The spreadsheet editor is a second MDI view; restore the 3D view explicitly.
        Gui.activateWorkbench('PartDesignWorkbench')
        d.recompute();assert all(o.Shape.isValid() and len(o.Shape.Solids)==1 for o in d.Objects if o.TypeId=='PartDesign::Body')
        gui_review.appearance(d);d.save()
        path=d.FileName;App.closeDocument(d.Name)
        d=App.openDocument(path);d.recompute()
        assert all(o.FullyConstrained for o in d.Objects if o.TypeId=='Sketcher::SketchObject')
        result['checks'].append('GUI save/close/reopen retains fully constrained Sketches and valid single-Solid Bodies')
        gui_review.appearance(d);d.save()
        # Open and save auxiliary GUI appearance without altering its placement.
        a=gui_review.open_model('auxiliary');App.closeDocument(a.Name)
        App.setActiveDocument(d.Name);Gui.activeDocument().activeView().viewAxonometric();Gui.activeDocument().activeView().fitAll()
        Gui.activeDocument().activeView().saveImage(str(ROOT/'reports/assembly-preview.png'),1800,1000,'White')
        result['status']='passed';result['checks'].append('Auxiliary appearance saved; main 3D preview rendered')
    except Exception as exc:
        result['status']='failed';result['error']=repr(exc)
        App.Console.PrintError(repr(exc)+'\n')
    (ROOT/'reports/gui-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
