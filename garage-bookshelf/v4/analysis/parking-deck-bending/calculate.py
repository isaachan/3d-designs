"""Read-only CAD study: quadratic solid FEA of the frozen reference parking deck.
Run with FreeCAD's bundled Python. Gmsh and CalculiX bundled with FreeCAD are used.
No assembly, STL or print project is modified. Output is confined to this folder.
"""
import sys,os,json,gzip,subprocess,tempfile,hashlib,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as App
import numpy as np
BIN=Path('/Applications/FreeCAD.app/Contents/Resources/bin')
DENSITY=1.24e-9 # tonne/mm^3; N, mm, s units
E=1000.0 # assumed reduced effective stiffness, NOT measured 25% infill material data
NU=.35
MODEL=ROOT/'reference/garage-bookshelf-v4-ribbed-analysis-source.FCStd'


def evaluate(doc,alias):
    value=doc.DesignParameters.evalExpression('DesignParameters.'+alias)
    return value.Value if hasattr(value,'Value') else float(value)


def set_value(doc,alias,value):
    # Resolve aliases on the frozen sheet, independently of production parameter rows.
    doc.DesignParameters.set(doc.DesignParameters.getCellFromAlias(alias),value)
    doc.recompute()


def run(command,folder,log):
    env=os.environ.copy();env['OMP_NUM_THREADS']='2';env['OPENBLAS_NUM_THREADS']='2'
    with (folder/log).open('w') as out:
        p=subprocess.run([str(x) for x in command],cwd=folder,env=env,stdout=out,stderr=subprocess.STDOUT)
    if p.returncode:raise RuntimeError(f'{command[0]} failed: {(folder/log).read_text()[-4000:]}')


def read_mesh(file):
    nodes={};elements={};mode=None
    for raw in file.read_text().splitlines():
        line=raw.strip()
        if line.startswith('**') or not line:continue
        if line.startswith('*'):
            line=line.upper();mode='node' if line.startswith('*NODE') else 'tet' if line.startswith('*ELEMENT') and 'TYPE=C3D10' in line.replace(' ','') else None
            continue
        if mode=='node':
            a=line.split(',');nodes[int(a[0])]=tuple(float(x) for x in a[1:4])
        elif mode=='tet':
            a=[int(x) for x in line.split(',') if x.strip()];assert len(a)==11,a
            elements[a[0]]=a[1:]
    used={n for el in elements.values() for n in el}
    nodes={n:nodes[n] for n in sorted(used)}
    assert nodes and elements
    return nodes,elements


def loads(nodes,points):
    top={n:p for n,p in nodes.items() if abs(p[2]-5)<1e-5};result={};patches=[]
    for x,y in points:
        ids=[n for n,p in top.items() if (p[0]-x)**2+(p[1]-y)**2<=4**2]
        assert ids,(x,y)
        for n in ids:result[n]=result.get(n,0)-1/len(points)/len(ids)
        patches.append(dict(centre=[x,y],node_count=len(ids)))
    assert abs(sum(result.values())+1)<1e-10
    return result,patches


def input_file(nodes,elements,centres):
    supports=[]
    for x,y in centres:
        ids=[n for n,p in nodes.items() if abs(p[2])<1e-5 and (p[0]-x)**2+(p[1]-y)**2<=10**2+1e-5]
        assert len(ids)>=5,(x,y,len(ids));supports.append(ids)
    a=min(supports[0],key=lambda n:(nodes[n][0]-centres[0][0])**2+(nodes[n][1]-centres[0][1])**2)
    b=min(supports[1],key=lambda n:(nodes[n][0]-centres[1][0])**2+(nodes[n][1]-centres[1][1])**2)
    # Three cars side-by-side, wheel track 20 mm and wheelbase 40 mm.
    points=[(cx+dx,79.3+dy) for cx in (50,99.8,149.6) for dx in (-10,10) for dy in (-20,20)]
    wheel,patches=loads(nodes,points)
    central,central_patch=loads(nodes,[(99.8,79.3)])
    lines=['*HEADING','Parking deck, homogeneous effective material, linear small displacement','*NODE,NSET=ALLN']
    lines += [f'{n},'+','.join(f'{v:.10g}' for v in p) for n,p in nodes.items()]
    lines += ['*ELEMENT,TYPE=C3D10,ELSET=ALL']
    lines += [str(e)+','+','.join(map(str,el)) for e,el in elements.items()]
    lines += ['*MATERIAL,NAME=EFFECTIVE_PLA','*ELASTIC',f'{E},{NU}','*DENSITY',str(DENSITY),'*SOLID SECTION,ELSET=ALL,MATERIAL=EFFECTIVE_PLA','*BOUNDARY']
    lines += [f'{n},3,3,0' for n in sorted(set(sum(supports,[])))]
    lines += [f'{a},1,2,0',f'{b},2,2,0']
    for case,force in [('self',None),('wheels_1N',wheel),('centre_1N',central)]:
        lines += ['*STEP','*STATIC','*DLOAD,OP=NEW',f'ALL,GRAV,{9810 if case=="self" else 0},0,0,-1']
        if force:
            lines += ['*CLOAD,OP=NEW']+[f'{n},3,{v:.12g}' for n,v in sorted(force.items())]
        lines += ['*NODE PRINT,NSET=ALLN','U,RF','*END STEP']
    return '\n'.join(lines)+'\n',dict(support_node_counts=list(map(len,supports)),support_nodes=supports,in_plane_pins=[a,b],wheel_patches=patches,central_patch=central_patch)


def read_results(file):
    data=[];mode=None;current=None
    for line in file.read_text().splitlines():
        if 'displacements (' in line:
            current=dict(u={},rf={});data.append(current);mode='u';continue
        if 'forces (' in line:mode='rf';continue
        if mode and re.match(r'^\s*\d+\s+[-+0-9.]',line):
            a=line.split()
            if len(a)==4:current[mode][int(a[0])]=[float(v.replace('D','E')) for v in a[1:]]
        elif line.strip() and not re.match(r'^\s*\d',line):mode=None
    assert len(data)==3,len(data)
    return data


def gravity_nodal_forces(nodes,elements):
    """Consistent C3D10 body forces; RF includes applied DLOAD at fixed nodes.
    Four-point integration matches the quadratic tetrahedron used in CalculiX.
    """
    connectivity=np.array(list(elements.values()),dtype=int)
    xyz=np.array([[nodes[n] for n in el] for el in connectivity])
    gradients=np.array([[-1,-1,-1],[1,0,0],[0,1,0],[0,0,1]],dtype=float)
    edges=[(0,1),(1,2),(2,0),(0,3),(1,3),(2,3)]
    ga=.5854101966249685;gb=.1381966011250105
    nodal=np.zeros((len(elements),10));volume=0.
    for corner in range(4):
        L=np.full(4,gb);L[corner]=ga
        N=np.r_[L*(2*L-1),[4*L[i]*L[j] for i,j in edges]]
        dN=np.vstack([(4*L-1)[:,None]*gradients,*[4*(L[i]*gradients[j]+L[j]*gradients[i]) for i,j in edges]])
        J=np.einsum('eni,nj->eij',xyz,dN)
        det=np.linalg.det(J);assert det.min()>0,det.min()
        volume+=det.sum()/24
        nodal+=det[:,None]*N[None,:]/24
    forces=np.zeros(max(nodes)+1)
    np.add.at(forces,connectivity.ravel(),(-nodal*DENSITY*9810).ravel())
    return forces,float(volume)


def solve(doc,h,size,folder):
    folder.mkdir()
    if h==0:
        tip=doc.garage_deck_1_Body.Tip
        shape=tip.BaseFeature.Shape.copy()
    else:
        set_value(doc,'DeckRibHeight',f'{h} mm');shape=doc.garage_deck_1_Body.Shape.copy()
    assert shape.isValid() and len(shape.Solids)==1
    shape.exportBrep(str(folder/'deck.brep'))
    # Gmsh's Abaqus writer supplies native C3D10 connectivity (no custom node-order conversion).
    run([BIN/'gmsh',folder/'deck.brep','-3','-order','2','-clmin',str(size),'-clmax',str(size),'-format','inp','-o',folder/'mesh.inp','-v','2'],folder,'gmsh.log')
    nodes,elements=read_mesh(folder/'mesh.inp')
    centres=[(evaluate(doc,x)-.2,evaluate(doc,y)-.2) for x,y in [('ColumnInset','ColumnInset'),('ColumnX2','ColumnInset'),('ColumnInset','ColumnY2'),('ColumnX2','ColumnY2')]]
    inp,setup=input_file(nodes,elements,centres);(folder/'case.inp').write_text(inp)
    run([BIN/'ccx','-i','case'],folder,'ccx.log')
    assert '*ERROR' not in (folder/'ccx.log').read_text()
    data=read_results(folder/'case.dat');ids=list(nodes)
    us=[np.array([case['u'][n][2] for n in ids]) for case in data]
    support_ids=set(sum(setup['support_nodes'],[]))
    raw_rf=[sum(case['rf'][n][2] for n in support_ids) for case in data]
    body_forces,mesh_volume=gravity_nodal_forces(nodes,elements)
    assert abs(mesh_volume-shape.Volume)/shape.Volume<.001,(mesh_volume,shape.Volume)
    reactions=raw_rf.copy();reactions[0]-=sum(body_forces[n] for n in support_ids)
    weight=shape.Volume*DENSITY*9810
    assert abs(reactions[0]-weight)<weight*.001,(reactions,weight)
    assert all(abs(v-1)<.005 for v in reactions[1:]),reactions
    scenarios=[]
    for mass_g in (50,60,100,200):
        force=3*mass_g/1000*9.81
        for arrangement,k in [('three_cars',1),('all_payload_at_centre',2)]:
            u=us[0]+force*us[k]
            scenarios.append(dict(per_car_g=mass_g,total_cars_g=3*mass_g,arrangement=arrangement,max_downward_mm=float(-u.min()),max_upward_mm=float(max(0,u.max())),at_xy_mm=list(nodes[ids[int(np.argmin(u))]][:2])))
    result=dict(rib_height_mm=h,mesh_size_mm=size,nodes=len(nodes),elements=len(elements),solid_volume_mm3=shape.Volume,self_mass_solid_upper_bound_g=shape.Volume*.00124,self_weight_N=weight,self_only_max_mm=float(-us[0].min()),wheel_load_compliance_mm_per_N=float(-us[1].min()),central_load_compliance_mm_per_N=float(-us[2].min()),reaction_sums_N=reactions,raw_rf_support_sums_N=raw_rf,mesh_quadrature_volume_mm3=mesh_volume,self_weight_equilibrium_relative_error=abs(reactions[0]-weight)/weight,setup=setup,scenarios=scenarios)
    # Save one displacement surface for plotting; solver meshes/results remain temporary.
    field={'node_ids':ids,'xyz':[nodes[n] for n in ids],'self_uz_mm':us[0].tolist(),'cars_1N_uz_mm':us[1].tolist(),'central_1N_uz_mm':us[2].tolist()}
    with gzip.open(ROOT/f'field-h{h:g}-mesh{size:g}.json.gz','wt') as output:
        json.dump(field,output,separators=(',',':'))
    print(json.dumps({k:result[k] for k in ['rib_height_mm','mesh_size_mm','nodes','elements','self_only_max_mm','central_load_compliance_mm_per_N']}),flush=True)
    return result


def main():
    model=MODEL;sha=hashlib.sha256(model.read_bytes()).hexdigest()
    doc=App.openDocument(str(model));result=[]
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--heights',default='0,2,3,4,6,8');parser.add_argument('--size',type=float,default=6);args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='parking-deck-fem-') as tmp:
        for h in map(float,args.heights.split(',')):
            result.append(solve(doc,h,args.size,Path(tmp)/f'h{h:g}-mesh{args.size:g}'))
            (ROOT/f'results-mesh{args.size:g}.json').write_text(json.dumps(dict(status='partial',E_effective_MPa=E,poisson_ratio=NU,cases=result),indent=2))
    App.closeDocument(doc.Name)
    assert hashlib.sha256(model.read_bytes()).hexdigest()==sha
    (ROOT/f'results-mesh{args.size:g}.json').write_text(json.dumps(dict(status='passed',method='quadratic C3D10 solids from exact CAD; local collar supports; linear isotropic effective material',model_sha256=sha,model_modified=False,E_effective_MPa=E,poisson_ratio=NU,cases=result),indent=2))

if __name__=='__main__':main()
