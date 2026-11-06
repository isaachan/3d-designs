"""Build spatially compatible, independent X2D decoration projects and slice them.

Uses the frozen assembly triangles. No native CAD or source geometry is changed.
Outputs only to a fresh build/ directory; promotion is a separate step.
"""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import subprocess
import _bootstrap
from _bootstrap import ROOT
from music_card_box.artifacts import export_3mf,write_json,sha
from verify import read_3mf_meshes

def bounds(vertices):
    return [min(v[i] for v in vertices) for i in range(3)]+[max(v[i] for v in vertices) for i in range(3)]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();out=args.output.resolve()
    if not out.is_relative_to(ROOT/'build') or out.exists():parser.error('Use a new directory under build/.')
    out.mkdir(parents=True)
    scene_path=ROOT/'printing/main/r1/evidence/scene.json'
    scene=json.loads(scene_path.read_text());colors=scene['spec']['colors']
    layout=json.loads((ROOT/'assets/print-layout.json').read_text())
    objects=[];checks={}
    for source in scene['objects']:
        name=source['name']
        if name not in layout['decoration_centers_xy_mm']:continue
        bb=bounds(source['vertices']);cx=(bb[0]+bb[3])/2;cz=(bb[2]+bb[5])/2
        tx,ty=layout['decoration_centers_xy_mm'][name]
        # Proper rotation, then XY translation. Place the real glue face at Z=0.
        vertices=[[v[0]-cx+tx,cz-v[2]+ty,v[1]-bb[1]] for v in source['vertices']]
        objects.append(dict(source,vertices=vertices))
        checks[name]={'bounds_mm':bounds(vertices),'triangles':len(source['faces'])}
    assert set(checks)==set(layout['decoration_centers_xy_mm'])
    main_mesh=read_3mf_meshes(ROOT/'printing/main/r1/01-darkblue.3mf')
    assert len(main_mesh)==1
    boxes={'CassetteShell':bounds(main_mesh[0][1]),**{n:v['bounds_mm'] for n,v in checks.items()}}
    envelope=layout['clearance_envelope_mm'];width,height=layout['bed_check_mm']
    for name,b in boxes.items():
        assert b[0]-envelope>=0 and b[1]-envelope>=0 and b[3]+envelope<=width and b[4]+envelope<=height,name
    separations=[]
    for i,(name,b) in enumerate(boxes.items()):
        for other,c in list(boxes.items())[i+1:]:
            gx=max(c[0]-b[3],b[0]-c[3]);gy=max(c[1]-b[4],b[1]-c[4])
            assert gx>2*envelope or gy>2*envelope,(name,other,gx,gy)
            separations.append({'pair':[name,other],'axis_gaps_mm':[gx,gy],'six_mm_envelopes_disjoint':True})
    profiles=ROOT/'assets/print-profiles';cli='/Applications/BambuStudio.app/Contents/MacOS/BambuStudio'
    runs=[]
    def run(label,args):
        cmd=[cli,'--debug','2','--datadir',str(out/('settings-'+label)),*args]
        r=subprocess.run(cmd,capture_output=True,text=True,cwd=out)
        (out/(label+'.log')).write_text(r.stdout+r.stderr)
        runs.append({'label':label,'exit_code':r.returncode,'command':cmd})
        if r.returncode:raise RuntimeError(f'{label} failed: {r.returncode}')
    for stem,color,expected in [('02-lightblue','lightblue',1),('03-white','white',3),('04-yellow','yellow',1)]:
        generic=out/(stem+'-geometry.3mf')
        export_3mf(generic,[o for o in objects if o['color']==color],colors)
        filament=json.loads((profiles/'PLA-darkblue.json').read_text())
        filament['filament_colour']=[colors[color]]
        filament_path=out/(stem+'-filament.json');write_json(filament_path,filament)
        run(stem+'-export',['--load-settings',str(profiles/'X2D-0.4-standard-machine.json')+';'+str(profiles/'PLA-0.20-process.json'),
            '--load-filaments',str(filament_path),'--arrange','0','--orient','0','--export-3mf',stem+'-candidate.3mf',
            '--outputdir',str(out),str(generic)])
        run(stem+'-reopen',['--export-settings',stem+'-settings.json','--export-3mf',stem+'.3mf',
            '--outputdir',str(out),str(out/(stem+'-candidate.3mf'))])
        meshes=read_3mf_meshes(out/(stem+'.3mf'));assert len(meshes)==expected
        # Check that the app preserved the planned positions and did not re-arrange.
        planned=[o for o in objects if o['color']==color]
        for mesh,source in zip(meshes,planned):
            actual=bounds(mesh[1]);target=bounds(source['vertices'])
            assert all(abs(a-b)<.00003 for a,b in zip(actual,target)),(stem,actual,target)
            assert len(mesh[2])==len(source['faces'])
        settings=json.loads((out/(stem+'-settings.json')).read_text())
        assert settings['brim_type']=='outer_only' and float(settings['brim_width'])==5
        slice_dir=out/(stem+'-slice');slice_dir.mkdir()
        run(stem+'-slice',['--slice','1','--export-3mf','slice-check.3mf','--outputdir',str(slice_dir),str(out/(stem+'.3mf'))])
        result=json.loads((slice_dir/'result.json').read_text())
        assert result['return_code']==0
        plate=result['sliced_plates'][0]
        assert len(plate['objects'])==expected,(stem,plate['objects'])
        assert not plate.get('warning_message'),plate.get('warning_message')
        assert plate['feature_type_times'].get('Brim',0)>0
        print('PASS',stem,expected,'objects, separated brim envelopes, actual slice',flush=True)
    # Reproduce the user's cross-file case on one plate. One filament keeps this
    # test focused on geometry/brim conflicts, independent of AMS/tool changes.
    combined=[{'name':'CassetteShell','color':'darkblue','vertices':main_mesh[0][1],'faces':main_mesh[0][2]},*objects]
    export_3mf(out/'combined-geometry.3mf',combined,colors)
    run('combined-export',['--load-settings',str(profiles/'X2D-0.4-standard-machine.json')+';'+str(profiles/'PLA-0.20-process.json'),
        '--load-filaments',str(profiles/'PLA-darkblue.json'),'--arrange','0','--orient','0',
        '--export-3mf','combined-candidate.3mf','--outputdir',str(out),str(out/'combined-geometry.3mf')])
    run('combined-reopen',['--export-3mf','combined.3mf','--outputdir',str(out),str(out/'combined-candidate.3mf')])
    combined_meshes=read_3mf_meshes(out/'combined.3mf');assert len(combined_meshes)==6
    for actual,expected in zip(combined_meshes,combined):
        assert all(abs(a-b)<.00003 for a,b in zip(bounds(actual[1]),bounds(expected['vertices'])))
    combined_slice=out/'combined-slice';combined_slice.mkdir()
    run('combined-slice',['--slice','1','--export-3mf','slice-check.3mf','--outputdir',str(combined_slice),str(out/'combined.3mf')])
    combined_result=json.loads((combined_slice/'result.json').read_text())
    assert combined_result['return_code']==0 and len(combined_result['sliced_plates'][0]['objects'])==6
    assert not combined_result['sliced_plates'][0].get('warning_message')
    print('PASS combined geometry/brim collision regression: all six objects on one plate',flush=True)
    write_json(out/'repack-validation.json',{'status':'passed','validated_at':datetime.now(timezone.utc).isoformat(),
        'source_scene':str(scene_path.relative_to(ROOT)),'source_scene_sha256':sha(scene_path),
        'source_cad_sha256':sha(ROOT/'cad/music-card-box-r1.FCStd'),'layout_sha256':sha(ROOT/'assets/print-layout.json'),
        'tool_sha256':sha(Path(__file__)),'parts':checks,'all_color_pairs':separations,'brim_width_mm':5,
        'bed_check_mm':layout['bed_check_mm'],'physical_print':'not_tested','runs':runs,
        'combined_slice_check':'passed; six objects, one-filament geometry/brim collision regression, no AMS validation',
        'files':{stem+'.3mf':sha(out/(stem+'.3mf')) for stem in ['02-lightblue','03-white','04-yellow']}})

if __name__=='__main__':main()
