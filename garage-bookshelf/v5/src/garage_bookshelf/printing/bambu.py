"""Bambu CLI helpers; importing does not generate files or refresh presets."""
import hashlib, json, subprocess, zipfile
from pathlib import Path
CLI=Path("/Applications/BambuStudio.app/Contents/MacOS/BambuStudio")
COLORS={'gray':'#8C949E','yellow':'#FABB1A','black':'#141414','white':'#F2F2F2','blue':'#1A5CE0'}

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

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
