"""Complete single-colour X2D projects; validation reopens the saved 3MF itself.
No printer connection is used. Temporary validation G-code is not delivered.
"""
import argparse,hashlib,json,re,shutil,subprocess,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
CLI=Path('/Applications/BambuStudio.app/Contents/MacOS/BambuStudio')
PRESETS=CLI.parent.parent/'Resources/profiles/BBL'
PROFILE_DIR=ROOT/'print-profiles'
COLORS={'gray':'#8C949E','yellow':'#FABB1A','black':'#141414','white':'#F2F2F2','blue':'#1A5CE0'}
PLATES=[
 ('01a-garage-deck-1-two-bays','gray',['garage_deck_1.stl'],1,False),
 ('01b-garage-deck-2-three-bays','gray',['garage_deck_2.stl'],1,False),
 ('01c-garage-deck-3-plain','gray',['garage_deck_3.stl'],1,False),
 ('02-garage-base','gray',['module_1.stl'],1,False),
 ('03-book-left','gray',['module_2.stl'],1,True),
 ('04-book-right','gray',['module_3.stl'],1,False),
 ('05-support-segments-twelve','yellow',['column_1_segment_1.stl']*12,1,False),
 ('06-top-segments-four','yellow',['column_1_segment_4.stl']*4,1,False),
 ('07-billboard-and-posts-black','black',['billboard.stl','billboard_post_left.stl','billboard_post_right.stl'],1,False),
 ('08-billboard-lettering-white','white',['billboard_text_lovely_cars.stl','billboard_text_ive_driven.stl'],1,False),
 ('09-blue-slogan-sign','blue',['book_depot_sign.stl'],1,False),
]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_profile(kind,name,sources,trail=()):
    """External CLI settings do not expand the system inherits/include chain."""
    assert name not in trail,(name,trail)
    path=PRESETS/kind/(name+'.json');data=json.loads(path.read_text());sources[str(path)]=sha(path)
    result={}
    if data.get('inherits'):result.update(resolve_profile(kind,data['inherits'],sources,trail+(name,)))
    for included in data.get('include',[]):result.update(resolve_profile(kind,included,sources,trail+(name,)))
    result.update(data)
    for key in ('inherits','include'):result.pop(key,None)
    return result


def prepare_profiles():
    PROFILE_DIR.mkdir(exist_ok=True);sources={}
    machine=resolve_profile('machine','Bambu Lab X2D 0.4 nozzle',sources)
    # Offline assumed hardware: one standard 0.4 nozzle per head, primary head used.
    # Official serializer: volume type + '#' + nozzle count, per extruder.
    # https://github.com/bambulab/BambuStudio/blob/master/src/libslic3r/PrintConfig.cpp
    machine.update(extruder_nozzle_stats=['Standard#1','Standard#1'],
                   nozzle_volume_type=['Standard','Standard'],curr_bed_type='Textured PEI Plate')
    assert len(machine['machine_start_gcode'])>10000 and 'X2D start gcode' in machine['machine_start_gcode']
    assert len(machine['machine_end_gcode'])>100
    m=PROFILE_DIR/'X2D-0.4-standard-machine.json';m.write_text(json.dumps(machine,ensure_ascii=False,indent=2))
    process=resolve_profile('process','0.20mm Standard @BBL X2D',sources)
    process.update(wall_loops='4',sparse_infill_density='25%',brim_width='4',brim_type='auto_brim',
                   enable_support='0',enable_prime_tower='0',curr_bed_type='Textured PEI Plate')
    processes={}
    for supports in (False,True):
        config=dict(process);config['enable_support']='1' if supports else '0'
        if supports:config.update(support_type='normal(auto)',support_on_build_plate_only='1')
        p=PROFILE_DIR/('PLA-0.20-support-process.json' if supports else 'PLA-0.20-process.json')
        p.write_text(json.dumps(config,ensure_ascii=False,indent=2));processes[supports]=p
    filament=resolve_profile('filament','Bambu PLA Basic @BBL X2D 0.4 nozzle',sources)
    assert float(filament['filament_density'][0])>1
    filaments={}
    for color,value in COLORS.items():
        config=dict(filament);config['filament_colour']=[value]
        p=PROFILE_DIR/f'PLA-{color}.json';p.write_text(json.dumps(config,ensure_ascii=False,indent=2));filaments[color]=p
    (PROFILE_DIR/'profile-sources.json').write_text(json.dumps(dict(
        source='installed Bambu Studio official presets; resolved inherits and include',
        source_files_sha256=sources,assumed_nozzles='two standard 0.4 mm; primary head used',
        default_bed='Textured PEI Plate',
        nozzle_stat_format_source='https://github.com/bambulab/BambuStudio/blob/master/src/libslic3r/PrintConfig.cpp'),indent=2))
    return m,processes,filaments


def run_cli(args,datadir,log):
    datadir.mkdir(parents=True,exist_ok=True)
    r=subprocess.run([str(CLI),'--debug','2','--datadir',str(datadir),*map(str,args)],capture_output=True,text=True,cwd=datadir)
    log.write_text('\n'.join(line.rstrip() for line in (r.stdout+'\n'+r.stderr).splitlines())+'\n')
    if r.returncode:raise RuntimeError(f'Bambu Studio failed ({r.returncode}); {log}:\n{log.read_text()[-4000:]}')
    return r


def read_settings(project,color,supports):
    with zipfile.ZipFile(project) as z:s=json.loads(z.read('Metadata/project_settings.config'))
    assert s['printer_model']=='Bambu Lab X2D' and s['nozzle_diameter']==['0.4','0.4']
    assert s['extruder_nozzle_stats']==['Standard#1','Standard#1']
    assert s['curr_bed_type']=='Textured PEI Plate' and s['filament_colour']==[COLORS[color]]
    assert float(s['filament_density'][0])>1 and 'X2D start gcode' in s['machine_start_gcode']
    assert len(s['machine_end_gcode'])>100
    for key,value in [('wall_loops','4'),('sparse_infill_density','25%'),('brim_width','4'),('layer_height','0.2'),('enable_support','1' if supports else '0')]:assert s[key]==value,(key,s[key])
    if supports:assert s['support_on_build_plate_only']=='1'
    keys=['printer_model','nozzle_diameter','extruder_nozzle_stats','curr_bed_type','filament_type','filament_colour','filament_density','textured_plate_temp','textured_plate_temp_initial_layer','nozzle_temperature','layer_height','wall_loops','sparse_infill_density','brim_width','brim_type','enable_support']
    return {key:s.get(key) for key in keys}


def main(only=None):
    machine,processes,filaments=prepare_profiles()
    output=ROOT/'bambu-projects';output.mkdir(exist_ok=True)
    logs=ROOT/'reports/slicing';logs.mkdir(exist_ok=True)
    source=ROOT/'print-stl';reports=[]
    previous={}
    if only:
        assert set(only)<={p[0] for p in PLATES}
        previous={Path(p['project']).stem:p for p in json.loads((ROOT/'slicer-validation.json').read_text())['projects']}
    with tempfile.TemporaryDirectory(prefix='garage-v4-print-') as scratch:
        temp=Path(scratch);staged=temp/'projects';staged.mkdir()
        for name,color,files,runs,supports in PLATES:
            if only and name not in only:
                row=dict(previous[name],validation_reused_with_matching_source_and_project_hashes=True)
                assert row['slice_status']=='passed'
                assert all(sha(source/f)==h for f,h in row['input_sha256'].items()),f'{name}: source changed; regenerate this plate'
                project=ROOT/row['project']
                if sha(project)!=row['project_sha256']:
                    # Retain a locally customized project; use its last validated delivery copy.
                    project=ROOT/'garage-bookshelf-v4-X2D-print-3mf'/project.name
                    assert sha(project)==row['project_sha256'],f'{name}: no unchanged validated copy'
                    row=dict(row,project=str(project.relative_to(ROOT)))
                reports.append(row)
                continue
            print(f'Preparing and reopening {name} ({color})',flush=True)
            project=staged/(name+'.3mf')
            run_cli(['--load-settings',f'{machine};{processes[supports]}','--load-filaments',filaments[color],
                     '--orient','0','--arrange','1','--export-3mf',project,*[source/f for f in files]],
                    temp/'export-state',logs/(name+'-export.log'))
            settings=read_settings(project,color,supports)
            # Slice the saved project, with no STL input or configuration override.
            sliced=temp/name;sliced.mkdir()
            run_cli(['--orient','0','--arrange','0','--outputdir',sliced,'--slice','0',project],
                    temp/'reload-state',logs/(name+'-reload-slice.log'))
            result=json.loads((sliced/'result.json').read_text())
            assert result['return_code']==0 and len(result['sliced_plates'])==1,result
            plate=result['sliced_plates'][0]
            assert not plate['warning_message'] and len(plate['objects'])==len(files),plate
            assert plate['filament_change_times']==0
            assert len(plate['filaments'])==1 and plate['filaments'][0]['total_used_g']>0
            assert abs(result['layer_height']-.2)<1e-6
            with zipfile.ZipFile(project) as z:(staged/(name+'.png')).write_bytes(z.read('Metadata/plate_1.png'))
            reports.append(dict(project=str((output/project.name).relative_to(ROOT)),project_sha256=sha(project),
                color=color,input_files=files,object_count=len(files),input_sha256={f:sha(source/f) for f in files},
                settings=settings,slice_status='passed',sliced_saved_3mf=True,reload_profile_overrides=False,
                print_runs=runs,slicer_warnings=[],estimated_seconds=round(plate['total_predication']),
                estimated_filament_g=plate['filaments'][0]['total_used_g']))
            (logs/(name+'-result.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2))
        # Publish only when all saved projects passed.
        for file in staged.iterdir():shutil.copy2(file,output/file.name)
    keep={name+ext for name,*_ in PLATES for ext in ('.3mf','.png')}
    for file in output.iterdir():
        if file.suffix in ('.3mf','.png') and file.name not in keep:file.unlink()
    version=subprocess.run([str(CLI),'--help'],capture_output=True,text=True).stdout
    report=dict(status='passed',bambu_studio=re.search(r'BambuStudio-([\d.]+)',version)[1],
        printer='Bambu Lab X2D, standard 0.4 mm nozzles',cad_sha256=sha(ROOT/'garage-bookshelf-v4-assembly.FCStd'),
        projects=reports,gcode_delivered=False,physical_print_completed=False,
        validation='each saved 3MF reopened and sliced without configuration override')
    (ROOT/'slicer-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    from package_print_projects import package_delivery
    package_delivery(report)
    print(f'PASS {len(reports)} saved 3MF projects; {sum(p["print_runs"] for p in reports)} print runs',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--only',nargs='+',choices=[p[0] for p in PLATES],help='Regenerate selected plates, checking hashes of reused plates and source meshes')
    main(parser.parse_args().only)
