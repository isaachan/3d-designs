# Frozen v4 source; use v5/tools or the migrated studies.
if __name__ == '__main__':
    raise SystemExit('Historical entry disabled; see v5/README.md and archive/README.md')

"""Slice replacement sign kit with v4 X2D presets, preserving all existing projects."""
import sys,json,tempfile,zipfile,shutil,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent))
# This file has the same name; load the v4 module explicitly.
import importlib.util
spec=importlib.util.spec_from_file_location('v4_print',ROOT.parent/'make_print_projects.py');base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
PLATES=[('01-top-receiver','black',['billboard.stl']),('02-top-carrier','black',['top_carrier.stl']),('03-side-receiver','blue',['side_receiver.stl']),('04-side-cartridge','blue',['side_cartridge.stl']),('05-lock-pins','yellow',['lock_pin_1.stl']*2),('00-fit-test','gray',['fit_receiver.stl','fit_carrier.stl'])]
def main(only=None,no_package=False):
    projects=ROOT/'bambu-projects';projects.mkdir(exist_ok=True);logs=ROOT/'reports';rows=[]
    m=ROOT.parent/'print-profiles/X2D-0.4-standard-machine.json';process=ROOT.parent/'print-profiles/PLA-0.20-process.json'
    previous={p['name']:p for p in json.loads((logs/'slicing.json').read_text())['projects']} if only else {}
    with tempfile.TemporaryDirectory(prefix='replaceable-signs-') as scratch:
        temp=Path(scratch)
        for name,color,files in PLATES:
            if only and name not in only:
                row=previous[name]
                assert base.sha(projects/(name+'.3mf'))==row['project_sha256']
                assert all(base.sha(ROOT/'print-stl'/f)==h for f,h in row['source_sha256'].items())
                rows.append(row);continue
            print('Preparing',name,flush=True);project=temp/(name+'.3mf')
            base.run_cli(['--load-settings',f'{m};{process}','--load-filaments',ROOT.parent/f'print-profiles/PLA-{color}.json','--orient','0','--arrange','1','--export-3mf',project,*[ROOT/'print-stl'/f for f in files]],temp/'export-state',logs/(name+'-export.log'))
            base.read_settings(project,color,False)
            sliced=temp/name;sliced.mkdir()
            base.run_cli(['--orient','0','--arrange','0','--outputdir',sliced,'--slice','0',project],temp/'reload-state',logs/(name+'-slice.log'))
            result=json.loads((sliced/'result.json').read_text());assert result['return_code']==0
            p=result['sliced_plates'][0];assert not p['warning_message'] and len(p['objects'])==len(files)
            shutil.copy2(project,projects/project.name)
            with zipfile.ZipFile(project) as z:(projects/(name+'.png')).write_bytes(z.read('Metadata/plate_1.png'))
            rows.append(dict(name=name,color=color,files=files,project_sha256=base.sha(project),source_sha256={f:base.sha(ROOT/'print-stl'/f) for f in files},reopened_and_sliced=True,estimated_seconds=p['total_predication'],estimated_filament_g=p['filaments'][0]['total_used_g'],warnings=p['warning_message']))
    (ROOT/'reports/slicing.json').write_text(json.dumps(dict(status='passed',projects=rows),ensure_ascii=False,indent=2))
    for ext in ['.3mf','.png']:(projects/('02-top-carriers'+ext)).unlink(missing_ok=True)
    if not no_package:package()
    print('PASS saved 3MF projects reopened and sliced',flush=True)
def package():
    # White letters are unchanged; include their previously sliced project so the kit is complete.
    old=json.loads((ROOT.parent/'slicer-validation.json').read_text())
    row=next(p for p in old['projects'] if Path(p['project']).stem=='08-billboard-lettering-white')
    original=ROOT.parent/row['project'];assert base.sha(original)==row['project_sha256']
    for f,h in row['input_sha256'].items():
        source=ROOT.parent/'print-stl'/f;assert base.sha(source)==h
        shutil.copy2(source,ROOT/'print-stl'/f)
    shutil.copy2(original,ROOT/'bambu-projects'/original.name)
    shutil.copy2(original.with_suffix('.png'),ROOT/'bambu-projects'/original.with_suffix('.png').name)
    (ROOT/'reports/reused-lettering.json').write_text(json.dumps(dict(status='passed',project=original.name,sha256=row['project_sha256'],source_sha256=row['input_sha256'],previous_saved_project_slice_reused=True),indent=2))
    with zipfile.ZipFile(ROOT/'removable-signs-print-kit.zip','w',zipfile.ZIP_DEFLATED) as z:
        for folder in ['bambu-projects','print-stl']:
            for f in sorted((ROOT/folder).iterdir()):z.write(f,folder+'/'+f.name)
        z.write(ROOT/'README.md','README.md')
        for f in (ROOT/'reports').glob('*.png'):z.write(f,'previews/'+f.name)
        for f in (ROOT/'reports').glob('*.json'):z.write(f,'reports/'+f.name)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--only',nargs='+',choices=[p[0] for p in PLATES]);parser.add_argument('--no-package',action='store_true');args=parser.parse_args();main(args.only,args.no_package)
