"""Promote an initial, validated candidate without overwriting formal artifacts."""
import argparse
import copy
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import subprocess
import _bootstrap
from _bootstrap import ROOT
from music_card_box.artifacts import sha,write_json

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',required=True,type=Path)
    parser.add_argument('--log',required=True,type=Path)
    args=parser.parse_args(); candidate=args.candidate.resolve()
    if not candidate.is_relative_to(ROOT/'build'): parser.error('Candidate must be under this project build/.')
    if (ROOT/'cad/music-card-box-r1.FCStd').exists():raise FileExistsError('Archive the existing formal revision before releasing a replacement.')
    report=json.loads((candidate/'validation.json').read_text())
    assert report['status']=='passed'
    for filename,expected in report['files'].items():assert sha(candidate/filename)==expected,filename
    for filename,expected in report['tool_sha256'].items():assert sha(ROOT/filename)==expected,filename
    assert sha(ROOT/'assets/design.json')==report['spec_sha256']
    if not (candidate/'preview-provenance.json').exists():
        write_json(candidate/'preview-provenance.json',{'render_input_scene_sha256':sha(candidate/'scene.json'),
            'current_scene_sha256':sha(candidate/'scene.json'),'identical_scene':True,
            'rendered_from_run':candidate.name,'current_geometry_run':candidate.name})
    if not (candidate/'import-result.json').exists():
        cli='/Applications/BambuStudio.app/Contents/MacOS/BambuStudio'
        imports={'status':'passed','tool':'BambuStudio --info','scope':'geometry import only; not slicing',
            'checked_at':datetime.now(timezone.utc).isoformat(),'files':{}}
        for stem,count in [('01-darkblue',1),('02-lightblue',1),('03-white',3),('04-yellow',1)]:
            log=candidate/(stem+'-import.log')
            if log.exists():raise FileExistsError(log)
            process=subprocess.run([cli,'--info',str(candidate/(stem+'.3mf'))],capture_output=True,text=True)
            log.write_text(process.stdout+process.stderr)
            assert process.returncode==0 and process.stdout.count('manifold = yes')==count,stem
            imports['files'][stem+'.3mf']={'exit_code':process.returncode,'manifold':True,'objects':count,'log':log.name}
        write_json(candidate/'import-result.json',imports)
    mainpath=Path('printing/main/r1');decor=Path('printing/decorations/cassette-r1')
    locations={
        'music-card-box-r1.FCStd':Path('cad/music-card-box-r1.FCStd'),
        'music-card-box-r1.step':Path('cad/music-card-box-r1.step'),
        'music-card-box-assembly.3mf':Path('printing/assembly/music-card-box-r1.3mf'),
        '01-darkblue.3mf':mainpath/'01-darkblue.3mf',
        '02-lightblue.3mf':decor/'02-lightblue.3mf',
        '03-white.3mf':decor/'03-white.3mf',
        '04-yellow.3mf':decor/'04-yellow.3mf',
        'scene.json':mainpath/'evidence/scene.json',
        'design-snapshot.json':mainpath/'evidence/design-snapshot.json',
        'preview-provenance.json':mainpath/'evidence/render/preview-provenance.json',
        'import-result.json':mainpath/'evidence/import-result.json'}
    imports=json.loads((candidate/'import-result.json').read_text())
    assert imports['status']=='passed' and len(imports['files'])==4
    for filename,entry in imports['files'].items():
        assert entry['exit_code']==0 and entry['manifold'] is True
        locations[entry['log']]=mainpath/'evidence/import'/entry['log']
    spec=json.loads((ROOT/'assets/design.json').read_text())
    for name in spec['print_parts']:
        parent=mainpath if name=='CassetteShell' else decor
        locations[name+'.stl']=parent/'evidence'/(name+'.stl')
    for filename in ['hero.png','empty.png','rear.png','dimensions.png']:
        locations[filename]=mainpath/filename
    targets=list(locations.values())+[Path('cad/model-spec.json'),Path('printing/catalog.json')]
    for component in [mainpath,decor]:
        targets.extend([component/'validation.json',component/'evidence/build.log'])
        targets.extend(component/'evidence/generator'/f for f in report['tool_sha256'])
        targets.extend(component/'evidence/generator'/f for f in ['tools/render.py','tools/dimensions.py'])
        targets.extend(component/'evidence/render'/(view+'-render.log') for view in ['hero','empty','rear'])
    assert len(targets)==len(set(targets))
    for target in targets:
        if (ROOT/target).exists():raise FileExistsError(ROOT/target)
    for filename,target in locations.items():
        assert (candidate/filename).is_file(),filename
    for filename,target in locations.items():
        (ROOT/target).parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(candidate/filename,ROOT/target)
    model={'revision':spec['revision'],'units':'mm','coordinates':{'x':'horizontal','y':'away from wall','z':'up'},
        'source':'cad/music-card-box-r1.FCStd','generator_input':'assets/design.json','parts':spec['print_parts'],
        'body_bounds_mm':[190.4,38.4,92],'maximum_depth_with_decoration_mm':42.2,
        'input_sha256':report['spec_sha256'],'reference_photo_sha256':sha(ROOT/'assets/reference/cards.jpg')}
    write_json(ROOT/'cad/model-spec.json',model)
    for component,scope in [(mainpath,'main'),(decor,'decorations')]:
        record=copy.deepcopy(report)
        record['scope']=scope
        record['artifact_locations']={filename:str(target) for filename,target in locations.items()}
        for filename in locations:
            record['files'][filename]=sha(candidate/filename)
        record['preview_note']='CAD triangles rendered without geometry changes; cards, printed score and yellow tape landing surfaces are illustrative.'
        record['slicer_import_check']=imports
        record['source_reference_photo_sha256']=model['reference_photo_sha256']
        record['preview_tools_sha256']={str(f.relative_to(ROOT)):sha(f) for f in [ROOT/'tools/render.py',ROOT/'tools/dimensions.py']}
        record['release_packaged_at']=datetime.now(timezone.utc).isoformat()
        write_json(ROOT/component/'validation.json',record)
        logpath=ROOT/component/'evidence/build.log';logpath.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(args.log,logpath)
        for view in ['hero','empty','rear']:
            target=ROOT/component/'evidence/render'/(view+'-render.log')
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(candidate/(view+'-render.log'),target)
        for source in report['tool_sha256']:
            target=ROOT/component/'evidence/generator'/source
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/source,target)
        for source in record['preview_tools_sha256']:
            target=ROOT/component/'evidence/generator'/source
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/source,target)
    files={str(path.relative_to(ROOT)):sha(path) for folder in ['cad','printing'] for path in sorted((ROOT/folder).rglob('*')) if path.is_file() and path.name!='catalog.json'}
    write_json(ROOT/'printing/catalog.json',{'revision':spec['revision'],'validated_at':report['validated_at'],
        'physical_fit':'not_tested','sliced':False,'machine_profile':None,
        'source_cad':'cad/music-card-box-r1.FCStd','source_cad_sha256':report['cad_sha256'],
        'components':{'main':str(mainpath),'decorations':str(decor)},'files':files})
    print('RELEASED',len(files),'files')

if __name__=='__main__': main()
