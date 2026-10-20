"""Verify frozen source hashes and delivery completeness, without modifying v2."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OLD=ROOT.parent/'v2'
inv=json.loads((ROOT/'reference/v2-inventory.json').read_text())
checks=[]
for item in inv['all_files']:
    path=OLD/item['path'];ok=path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256']
    checks.append(dict(path=item['path'],unchanged=ok))
assert all(x['unchanged'] for x in checks)
required=['garage-bookshelf-v3-assembly.FCStd','garage-bookshelf-v3-auxiliary.FCStd','representative.FCStd','README.md','reports/validation-summary.md','reports/parameters.md','reports/bom.json','reports/geometry-comparison.json','reports/parametric-validation.json','reports/reopen-validation.json','reports/print-validation.json']
assert all((ROOT/p).is_file() for p in required)
assert {p.stem for p in (ROOT/'stl').glob('*.stl')}=={p.stem for p in (OLD/'stl').glob('*.stl')}
assert len(list((ROOT/'print-stl').glob('*.stl')))==34
assert len(list((ROOT/'body-stl').glob('*.stl')))==52
result=dict(status='passed',source_file_count=len(checks),source_files_unchanged=True,checks=checks,required_deliverables=required)
(ROOT/'reports/source-integrity.json').write_text(json.dumps(result,indent=2))
print(f'All {len(checks)} v2 source files unchanged; all required deliverables exist.')
