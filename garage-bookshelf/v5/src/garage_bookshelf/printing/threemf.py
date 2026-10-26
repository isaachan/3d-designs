"""Check final 3MF coordinates and save checksums of delivered artifacts."""
import hashlib,json,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
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
