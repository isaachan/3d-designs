import sys,json,zipfile,hashlib,xml.etree.ElementTree as E
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from make_print_projects import run_cli,CLI
OUT=Path(__file__).resolve().parent/'artifacts';OUT.mkdir(exist_ok=True)
WORK=Path(__file__).resolve().parent/'work';WORK.mkdir(exist_ok=True)
project=OUT/'back-joint-six-fit-tests.3mf'
files=[OUT/f'{tag}-{sex}.stl' for tag in 'ABCDEF' for sex in ('M','S')]
run_cli(['--load-settings',f'{ROOT}/print-profiles/X2D-0.4-standard-machine.json;{ROOT}/print-profiles/PLA-0.20-support-process.json','--load-filaments',ROOT/'print-profiles/PLA-blue.json','--orient','0','--arrange','1','--export-3mf',project,*files],WORK/'export-state',WORK/'export.log')
# v4 book-left (male) uses bed-only support; book-right (socket) has support off.
with zipfile.ZipFile(project) as z:items={n:z.read(n) for n in z.namelist()}
cfg=E.fromstring(items['Metadata/model_settings.config']);count=0
for obj in cfg.findall('object'):
 name=next(m.get('value') for m in obj.findall('metadata') if m.get('key')=='name')
 E.SubElement(obj,'metadata',key='enable_support',value='0' if '-S' in name else '1');count+=1
assert count==12
items['Metadata/model_settings.config']=E.tostring(cfg,encoding='utf-8',xml_declaration=True)
with zipfile.ZipFile(project,'w',zipfile.ZIP_DEFLATED) as z:
 for n,b in items.items():z.writestr(n,b)
settings=json.loads(items['Metadata/project_settings.config'])
assert settings['printer_model']=='Bambu Lab X2D' and settings['nozzle_diameter']==['0.4','0.4']
assert settings['xy_contour_compensation']=='0' and settings['xy_hole_compensation']=='0'
result_dir=WORK/'sliced';result_dir.mkdir(exist_ok=True)
run_cli(['--orient','0','--arrange','0','--outputdir',result_dir,'--slice','0',project],WORK/'reload-state',WORK/'slice.log')
r=json.loads((result_dir/'result.json').read_text());assert r['return_code']==0 and len(r['sliced_plates'])==1
p=r['sliced_plates'][0];assert len(p['objects'])==12 and not p['warning_message'],p
assert len(p['filaments'])==1
from check_package import project_bounds
bounds=project_bounds(project);assert len(bounds)==12
(OUT/'plate-preview.png').write_bytes(items['Metadata/plate_1.png'])
(OUT/'validation.json').write_text(json.dumps(dict(status='passed',objects=12,pairs=6,saved_3mf_reopened_and_sliced=True,slice_overrides=False,object_supports='M on, S off; build plate only',warnings=p['warning_message'],estimated_hours=p['total_predication']/3600,estimated_filament_g=p['filaments'][0]['total_used_g'],sha256=hashlib.sha256(project.read_bytes()).hexdigest(),object_bounds=bounds,physical_fit='not_tested'),indent=2))
print('PASS saved 3MF reopened and sliced: 12 objects, one plate, no warnings; hours',p['total_predication']/3600,'grams',p['filaments'][0]['total_used_g'],flush=True)
