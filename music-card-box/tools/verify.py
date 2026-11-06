"""Read-only hashes, native document structure, 3MF topology and local links."""
from collections import Counter
import json
from pathlib import Path
import re
from zipfile import ZipFile
import xml.etree.ElementTree as ET
import _bootstrap
from _bootstrap import ROOT
from music_card_box.artifacts import sha

def saved_projects():
    path=ROOT/'printing/saved-projects-20261106.json'
    return json.loads(path.read_text())['projects'] if path.exists() else {}

def check_manifest():
    catalog=json.loads((ROOT/'printing/catalog.json').read_text())
    for filename,expected in catalog['files'].items():
        path=(ROOT/filename).resolve();assert path.is_relative_to(ROOT),filename
        assert sha(path)==expected,filename
    for path in (ROOT/'printing').rglob('validation.json'):
        report=json.loads(path.read_text())
        for filename,expected in report['files'].items():
            assert sha(ROOT/report['artifact_locations'][filename])==expected,filename
        for source,expected in report['tool_sha256'].items():
            assert sha(path.parent/'evidence/generator'/source)==expected,source
            assert sha(ROOT/source)==expected,source
        for source,expected in report['preview_tools_sha256'].items():
            assert sha(path.parent/'evidence/generator'/source)==expected,source
            assert sha(ROOT/source)==expected,source
        assert sha(ROOT/'assets/design.json')==report['spec_sha256']
        assert sha(ROOT/'assets/reference/cards.jpg')==report['source_reference_photo_sha256']
        assert report['slicing'] in ['not_performed_printer_unspecified','passed_x2d_0p4_pla_brim5','passed_x2d_0p4_pla_decoration_layout_r2']
    for filename,record in saved_projects().items():
        assert sha(ROOT/filename)==record['sha256'],filename
        assert sha(ROOT/record['reference'])==record['reference_sha256']
        assert sha(ROOT/record['slice_result'])==record['slice_result_sha256']
        result=json.loads((ROOT/record['slice_result']).read_text())
        assert result['return_code']==0 and not result['sliced_plates'][0].get('warning_message')
        current=read_3mf_meshes(ROOT/filename);previous=read_3mf_meshes(ROOT/record['reference'])
        assert len(current)==len(previous)==len(record['translations_mm'])
        for actual,prior,delta in zip(current,previous,record['translations_mm']):
            assert actual[2]==prior[2] and len(actual[1])==len(prior[1])
            assert max(abs(a[i]-b[i]-delta[i]) for a,b in zip(actual[1],prior[1]) for i in range(3))<.00002
    with ZipFile(ROOT/catalog['source_cad']) as z:
        doc=ET.fromstring(z.read('Document.xml'))
        objects=doc.find('Objects')
        assert sum(o.get('type')=='PartDesign::Body' for o in objects)==6
        assert sum(o.get('type')=='Sketcher::SketchObject' for o in objects)>=10
        assert 'GuiDocument.xml' in z.namelist()
        gui=ET.fromstring(z.read('GuiDocument.xml'))
        assert 'height 150' in gui.find('Camera').get('settings')
    return len(catalog['files'])

def mesh_volume(vertices,faces):
    result=0
    for i,j,k in faces:
        a,b,c=vertices[i],vertices[j],vertices[k]
        result+=a[0]*(b[1]*c[2]-b[2]*c[1])+a[1]*(b[2]*c[0]-b[0]*c[2])+a[2]*(b[0]*c[1]-b[1]*c[0])
    return result/6

def read_3mf_meshes(path):
    """Read build instances, including Bambu production components/transforms."""
    ns={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
    prod='{http://schemas.microsoft.com/3dmanufacturing/production/2015/06}'
    identity='1 0 0 0 1 0 0 0 1 0 0 0'
    import posixpath
    meshes=[]
    with ZipFile(path) as z:
        roots={}
        def root_for(filename):
            if filename not in roots:roots[filename]=ET.fromstring(z.read(filename))
            assert roots[filename].get('unit')=='millimeter'
            return roots[filename]
        def walk(filename,objectid,transforms):
            root=root_for(filename)
            obj=next(o for o in root.findall('m:resources/m:object',ns) if o.get('id')==objectid)
            if obj.find('m:mesh',ns) is not None:
                vertices=[[float(v.get(a)) for a in ['x','y','z']] for v in obj.findall('m:mesh/m:vertices/m:vertex',ns)]
                faces=[[int(t.get(a)) for a in ['v1','v2','v3']] for t in obj.findall('m:mesh/m:triangles/m:triangle',ns)]
                for transform in reversed(transforms):
                    m=list(map(float,transform.split()))
                    vertices=[[m[i]*v[0]+m[3+i]*v[1]+m[6+i]*v[2]+m[9+i] for i in range(3)] for v in vertices]
                meshes.append((obj.get('name',objectid),vertices,faces))
            for component in obj.findall('m:components/m:component',ns):
                ref=component.get(prod+'path')
                target=filename if ref is None else ref.lstrip('/') if ref.startswith('/') else posixpath.normpath(posixpath.join(posixpath.dirname(filename),ref))
                walk(target,component.get('objectid'),transforms+[component.get('transform',identity)])
        for item in root_for('3D/3dmodel.model').findall('m:build/m:item',ns):
            walk('3D/3dmodel.model',item.get('objectid'),[item.get('transform',identity)])
    return meshes

def check_3mf():
    count=0
    print_boxes=[]
    saved=saved_projects()
    for path in sorted((ROOT/'printing').rglob('*.3mf')):
        record=saved.get(str(path.relative_to(ROOT)))
        bed=record['independent_bed_mm'] if record else [220,220]
        for name,vertices,faces in read_3mf_meshes(path):
                assert vertices and faces,path
                edges=Counter()
                for f in faces:
                    assert len(set(f))==3
                    for a,b in zip(f,f[1:]+f[:1]):edges[(a,b)]+=1
                assert all(v==1 and edges[(b,a)]==1 for (a,b),v in edges.items()),(path,name,'non-manifold/winding')
                assert mesh_volume(vertices,faces)>0,(path,name,'inward normals')
                if path.parent.name!='assembly':
                    assert abs(min(v[2] for v in vertices))<1e-5,path
                    assert all(0<=v[0]<bed[0] and 0<=v[1]<bed[1] for v in vertices),path
                    if not record:
                        print_boxes.append((str(path)+':'+name,[min(v[i] for v in vertices) for i in range(2)]+[max(v[i] for v in vertices) for i in range(2)]))
                count+=1
        if record:
            # Recheck the original combined-layout contract at its frozen pose.
            # Subsequent manual saves are independent print projects.
            for name,vertices,faces in read_3mf_meshes(ROOT/record['reference']):
                print_boxes.append((str(path)+':'+name,[min(v[i] for v in vertices) for i in range(2)]+[max(v[i] for v in vertices) for i in range(2)]))
            with ZipFile(path) as z:
                settings=json.loads(z.read('Metadata/project_settings.config'))
                assert all(settings.get(k)==v for k,v in record['settings'].items())
    assert count==12,count # Six print objects plus six assembly objects.
    # All color files may be imported together: preserve a 6 mm allowance around
    # every footprint, covering the configured 5 mm brim plus path clearance.
    for i,(name,b) in enumerate(print_boxes):
        for other,c in print_boxes[i+1:]:
            gx=max(c[0]-b[2],b[0]-c[2]);gy=max(c[1]-b[3],b[1]-c[3])
            assert gx>12 or gy>12,(name,other,'overlapping brim envelopes')
    main=ROOT/'printing/main/r1/01-darkblue.3mf'
    with ZipFile(main) as z:
        settings=json.loads(z.read('Metadata/project_settings.config'))
        expected=saved.get(str(main.relative_to(ROOT)),{}).get('settings',{'brim_type':'outer_only','brim_width':'5'})
        assert settings['brim_type']==expected['brim_type'] and float(settings['brim_width'])==float(expected['brim_width'])
        assert settings['printer_model']=='Bambu Lab X2D'
        model=ET.fromstring(z.read('Metadata/model_settings.config'))
        assert len(model.findall('plate/model_instance'))==1
        assert not any(name.endswith('.gcode') for name in z.namelist())
    for stem,objects in [('02-lightblue',1),('03-white',3),('04-yellow',1)]:
        with ZipFile(ROOT/'printing/decorations/cassette-r1'/(stem+'.3mf')) as z:
            settings=json.loads(z.read('Metadata/project_settings.config'))
            assert settings['printer_model']=='Bambu Lab X2D'
            key='printing/decorations/cassette-r1/'+stem+'.3mf'
            expected=saved.get(key,{}).get('settings',{'brim_type':'outer_only','brim_width':'5'})
            assert settings['brim_type']==expected['brim_type'] and float(settings['brim_width'])==float(expected['brim_width'])
            model=ET.fromstring(z.read('Metadata/model_settings.config'))
            assert len(model.findall('plate/model_instance'))==objects
            assert not any(name.endswith('.gcode') for name in z.namelist())
    return count

def check_links():
    count=0
    for path in ROOT.rglob('*.md'):
        if any(part in ['build','archive'] for part in path.relative_to(ROOT).parts):continue
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)',path.read_text()):
            if '://' in target or target.startswith('#'):continue
            target=target.split('#')[0]
            assert (path.parent/target).exists(),(path,target)
            count+=1
    return count

def main():
    print('PASS',check_manifest(),'manifest entries;',check_3mf(),'closed outward 3MF meshes;',check_links(),'local links')

if __name__=='__main__':main()
