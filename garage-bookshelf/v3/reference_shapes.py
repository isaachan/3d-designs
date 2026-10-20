"""Audit-only exact v2 design oracle. No legacy object or mesh becomes v3 geometry."""
import ast, json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OLD=ROOT.parent/'v2'
def namespace():
    tree=ast.parse((OLD/'generate_v2.py').read_text())
    allowed=[]
    for node in tree.body:
        if isinstance(node,(ast.Import,ast.ImportFrom,ast.FunctionDef)):
            allowed.append(node)
        elif isinstance(node,ast.Assign):
            names=[t.id for t in node.targets if isinstance(t,ast.Name)]
            if names==['modules']: break
            allowed.append(node)
    ns={'__file__':str(OLD/'generate_v2.py')}
    exec(compile(ast.Module(body=allowed,type_ignores=[]),'v2-readonly-design-oracle','exec'),ns)
    return ns

def shapes():
    n=namespace();A=n['App'];P=n['Part'];out={}
    for i,(x0,x1) in enumerate(zip(n['CUTS'],n['CUTS'][1:]),1): out[f'module_{i}']=n['make_module'](i,x0,x1)
    out['module_2_narrow_visual']=n['shortened_visual_module'](out['module_2'],180,215,345,423.8)
    out['module_5_narrow_visual']=n['shortened_visual_module'](out['module_5'],770,800,900,920)
    for lev,z in enumerate((66,129,192),1):
        for side in ('left','right'): out[f'garage_deck_{lev}_{side}']=n['deck_half']('',side=='right',z)
        out[f'garage_deck_{lev}_seam_bridge']=n['deck_seam_bridge'](z)
    for i in range(1,5): out[f'garage_column_{i}']=n['column']()
    out['book_depot_sign']=n['panel_shape'](36,180,6)
    for name,dims,pos in [('billboard_left',(180,6,64),(0,220,300)),('billboard_right',(180,6,64),(180,220,300)),('billboard_seam_bridge',(50,3,36),(155,226,314)),('billboard_post_left',(24,6,150),(78,220,150)),('billboard_post_right',(24,6,150),(258,220,150))]: out[name]=P.makeBox(*dims,A.Vector(*pos))
    masks=json.loads((ROOT/'reference/text-masks.json').read_text())
    for name,z in [('billboard_text_lovely_cars',332),('billboard_text_ive_driven',304)]:
        boxes=[P.makeBox(run+.1,1,1.1,A.Vector(90+x-.05,219,z+y-.05)) for x,y,run in masks[name]]
        out[name]=boxes[0].multiFuse(boxes[1:]).removeSplitter()
    # Capture all six test parts without invoking the legacy export function.
    n['export']=lambda name,shape,**kw:out.__setitem__(name,shape)
    n['test_shapes']()
    return out

def freeze_masks():
    masks={}
    for name,text in [('billboard_text_lovely_cars','Lovely Cars'),('billboard_text_ive_driven',"I've Driven")]:
        masks[name]=json.loads(subprocess.check_output(['/usr/bin/swift',str(OLD/'generate-label-mask.swift'),text,'26','180','28','horizontal'],text=True))
    (ROOT/'reference/text-masks.json').write_text(json.dumps(masks,indent=2))
if __name__=='__main__': freeze_masks()
