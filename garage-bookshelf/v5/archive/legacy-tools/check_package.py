# Frozen v4 source; use v5/tools or the migrated studies.
if __name__ == '__main__':
    raise SystemExit('Historical entry disabled; see v5/README.md and archive/README.md')

"""Check final 3MF coordinates and save checksums of delivered artifacts."""
import hashlib,json,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parent
NS={'c':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02','p':'http://schemas.microsoft.com/3dmanufacturing/production/2015/06'}
IDENTITY=[1,0,0,0,1,0,0,0,1,0,0,0]


def transform(points,text):
    m=list(map(float,text.split())) if text else IDENTITY
    return [[sum(p[j]*m[3*j+i] for j in range(3))+m[9+i] for i in range(3)] for p in points]


def project_bounds(file):
    with zipfile.ZipFile(file) as z:
        trees={}
        def model(path):
            path=path.lstrip('/')
            if path not in trees:trees[path]=ET.fromstring(z.read(path))
            return trees[path]
        def points(path,oid):
            obj=next(o for o in model(path).findall('c:resources/c:object',NS) if o.get('id')==oid)
            mesh=obj.find('c:mesh',NS)
            if mesh is not None:
                return [[float(v.get(k)) for k in 'xyz'] for v in mesh.findall('c:vertices/c:vertex',NS)]
            result=[]
            for c in obj.findall('c:components/c:component',NS):
                target=c.get('{'+NS['p']+'}path',path)
                result.extend(transform(points(target,c.get('objectid')),c.get('transform')))
            return result
        result=[]
        assert model('3D/3dmodel.model').get('unit')=='millimeter'
        for item in model('3D/3dmodel.model').findall('c:build/c:item',NS):
            pp=transform(points('3D/3dmodel.model',item.get('objectid')),item.get('transform'))
            lo=[min(p[i] for p in pp) for i in range(3)];hi=[max(p[i] for p in pp) for i in range(3)]
            assert lo[0]>=24.5-.01 and hi[0]<=252+.01,(file,lo,hi)
            assert lo[1]>=4-.01 and hi[1]<=252+.01,(file,lo,hi)
            assert abs(lo[2])<.01 and hi[2]<=256+.01,(file,lo,hi)
            result.append(dict(min_mm=lo,max_mm=hi))
        return result


def main():
    checks=[]
    slicer=json.loads((ROOT/'slicer-validation.json').read_text())
    assert len(slicer['projects'])==11
    assert hashlib.sha256((ROOT/'garage-bookshelf-v4-assembly.FCStd').read_bytes()).hexdigest()==slicer['cad_sha256']
    for p in slicer['projects']:
        assert p['slice_status']=='passed' and p['sliced_saved_3mf'] and not p['reload_profile_overrides']
        assert all(hashlib.sha256((ROOT/'print-stl'/f).read_bytes()).hexdigest()==h for f,h in p['input_sha256'].items())
        file=ROOT/p['project']
        assert hashlib.sha256(file.read_bytes()).hexdigest()==p['project_sha256']
        bounds=project_bounds(file)
        assert len(bounds)==p['object_count']
        checks.append(dict(project=p['project'],object_bounds=bounds,within_x_20_5_to_256_y_0_to_256_with_4mm_brim=True))
    assert [p['object_count'] for p in slicer['projects']]==[1,1,1,1,1,1,12,4,3,2,1]
    assert [p['input_files'] for p in slicer['projects'][:3]]==[[f'garage_deck_{lev}.stl'] for lev in (1,2,3)]
    assert all(p['print_runs']==1 for p in slicer['projects'])
    assert sum(p['print_runs'] for p in slicer['projects'])==11
    exports=json.loads((ROOT/'reports/validation.json').read_text())['print_parts']
    components={Path(r['file']).name:r['solid_components'] for r in exports}
    physical_solids=sum(sum(components[f] for f in p['input_files'])*p['print_runs'] for p in slicer['projects'])
    assert physical_solids==46
    # All output artifacts are reviewable locally; no machine job is submitted.
    artifacts=[p for p in ROOT.rglob('*') if p.is_file() and p.suffix.lower() in ['.fcstd','.step','.stl','.3mf','.png','.zip']]
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(artifacts)}
    (ROOT/'reports/package-validation.json').write_text(json.dumps(dict(status='passed',print_runs=11,physical_solids=physical_solids,projects=checks,artifacts_sha256=hashes),ensure_ascii=False,indent=2))
    print('PASS final 3MF placement, counts, 11 print runs,',len(hashes),'artifacts')

if __name__=='__main__':main()
