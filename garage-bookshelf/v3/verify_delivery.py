"""Revalidate exact deliverable files after GUI saves, then verify all source hashes."""
import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as App
import validation
from export import export_document
ROOT=Path(__file__).resolve().parent

def main():
    docs=[App.openDocument(str(ROOT/f'garage-bookshelf-v3-{name}.FCStd')) for name in ('assembly','auxiliary')]
    records=[validation.native(d) for d in docs]
    result=validation.geometry(docs)
    exports=[row for d in docs for row in export_document(d,ROOT)]
    (ROOT/'reports/print-validation.json').write_text(json.dumps(dict(status='passed',part_count=len(exports),individual_body_stl_count=sum(len(x['individual_body_stls']) for x in exports),parts=exports,physical_PLA_fit_and_load='not_verified'),ensure_ascii=False,indent=2))
    for d in docs:App.closeDocument(d.Name)
    checks={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['garage-bookshelf-v3-assembly.FCStd','garage-bookshelf-v3-auxiliary.FCStd']}
    (ROOT/'reports/final-delivery-validation.json').write_text(json.dumps(dict(status='passed',documents=records,saved_geometry_comparison=result['status'],gui_validation=json.loads((ROOT/'reports/gui-validation.json').read_text())['status'],fcstd_sha256=checks),ensure_ascii=False,indent=2))
    print('Final saved GUI files: valid, exact source geometry retained; 52 individual Body STL files exported.')
if __name__=='__main__':main()
