"""Build a Bambu X2D project with an explicit 5 mm outer brim, then reopen it.

Frozen profiles live within this project; no other project's files are modified.
Output must be a new build/ directory. This does not replace formal delivery.
"""
import argparse
import json
from pathlib import Path
import subprocess
import _bootstrap
from _bootstrap import ROOT

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=ROOT/'printing/main/r1/01-darkblue.3mf')
    p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();out=a.output.resolve()
    if not out.is_relative_to(ROOT/'build') or out.exists():p.error('Use a new directory under build/.')
    out.mkdir(parents=True)
    profiles=ROOT/'assets/print-profiles';cli='/Applications/BambuStudio.app/Contents/MacOS/BambuStudio'
    def run(name,args):
        cmd=[cli,'--debug','2','--datadir',str(out/('settings-'+name)),*args]
        r=subprocess.run(cmd,capture_output=True,text=True,cwd=out)
        (out/(name+'.log')).write_text(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(f'{name} failed: {r.returncode}')
    run('export',['--load-settings',str(profiles/'X2D-0.4-standard-machine.json')+';'+str(profiles/'PLA-0.20-process.json'),
        '--load-filaments',str(profiles/'PLA-darkblue.json'),'--arrange','0','--orient','0',
        '--export-3mf','candidate.3mf','--outputdir',str(out),str(a.source.resolve())])
    # A second save registers generic-input models as real plate instances.
    run('reopen',['--export-settings','reopened-settings.json','--export-3mf','01-darkblue.3mf',
        '--outputdir',str(out),str(out/'candidate.3mf')])
    settings=json.loads((out/'reopened-settings.json').read_text())
    assert settings['brim_type']=='outer_only' and float(settings['brim_width'])==5
    print('PASS',out/'01-darkblue.3mf')

if __name__=='__main__':main()
