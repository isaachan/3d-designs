"""Generate v3 only after source/spec and representative gates pass."""
import sys,json,argparse
from pathlib import Path
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
ROOT=Path(__file__).resolve().parent
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
import FreeCAD as App
import build,validation,parameters
from export import export_document

def main():
    for gate in ['01-reference-crosscheck.json','03-representative-validation.json']:
        if not (ROOT/'reports'/gate).exists() or json.loads((ROOT/'reports'/gate).read_text())['status']!='passed':raise RuntimeError(f'Prerequisite not passed: {gate}; run verify_reference.py then representative.py')
    parameters.describe(ROOT)
    print('Building production assembly...',flush=True);d=build.assembly();print('Building auxiliaries...',flush=True);a=build.auxiliary()
    nr=[validation.native(x) for x in (d,a)]
    print('Testing parameter edits...',flush=True);param=validation.parameter_tests(d)
    (ROOT/'reports/parametric-validation.json').write_text(json.dumps(dict(status='passed',documents=nr,parameter_tests=param),ensure_ascii=False,indent=2))
    print('Comparing all 34 source parts...',flush=True);geo=validation.geometry((d,a))
    print('Checking assembly paths and retained interferences...',flush=True);assembly=validation.assembly_checks(d)
    (ROOT/'reports/assembly-validation.json').write_text(json.dumps(assembly,ensure_ascii=False,indent=2))
    print('Exporting and checking STL...',flush=True);exports=[]
    for x in (d,a):exports.extend(export_document(x,ROOT))
    (ROOT/'reports/print-validation.json').write_text(json.dumps(dict(status='passed',part_count=len(exports),parts=exports,physical_PLA_fit_and_load='not_verified'),ensure_ascii=False,indent=2))
    paths=[ROOT/'garage-bookshelf-v3-assembly.FCStd',ROOT/'garage-bookshelf-v3-auxiliary.FCStd']
    for doc,path in zip((d,a),paths):doc.recompute();doc.saveAs(str(path));App.closeDocument(doc.Name)
    print('Reopening saved projects...',flush=True)
    reopened=[validation.reopen(p,n) for p,n in zip(paths,(44,8))]
    (ROOT/'reports/reopen-validation.json').write_text(json.dumps(dict(status='passed',documents=reopened),ensure_ascii=False,indent=2))
    print('V3 reconstruction completed; see reports for inherited design issues.',flush=True)
if __name__=='__main__':main()
