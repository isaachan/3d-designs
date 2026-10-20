"""Summarize results and render an exportable engineering figure."""
import gzip,json,hashlib,csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,Circle
ROOT=Path(__file__).resolve().parent


def scenario(case,mass,arrangement):
    return next(s['max_downward_mm'] for s in case['scenarios'] if s['per_car_g']==mass and s['arrangement']==arrangement)


def main():
    coarse=json.loads((ROOT/'results-mesh6.json').read_text())
    fine=json.loads((ROOT/'results-mesh4.json').read_text())
    assert coarse['status']==fine['status']=='passed'
    assert coarse['model_sha256']==fine['model_sha256']
    model=ROOT/'reference/garage-bookshelf-v4-ribbed-analysis-source.FCStd'
    assert hashlib.sha256(model.read_bytes()).hexdigest()==fine['model_sha256']
    by_coarse={c['rib_height_mm']:c for c in coarse['cases']}
    by_fine={c['rib_height_mm']:c for c in fine['cases']}
    convergence=[]
    for h,f in by_fine.items():
        for mass,arrangement in [(60,'three_cars'),(100,'all_payload_at_centre'),(200,'all_payload_at_centre')]:
            a=scenario(by_coarse[h],mass,arrangement);b=scenario(f,mass,arrangement)
            error=abs(a-b)/b
            assert error<.05,(h,error)
            convergence.append(dict(rib_height_mm=h,per_car_g=mass,arrangement=arrangement,mesh6_mm=a,mesh4_mm=b,relative_difference=error))
    rows=[]
    for h,c in by_coarse.items():
        used=by_fine.get(h,c)
        rows.append(dict(rib_height_mm=h,source_mesh_mm=used['mesh_size_mm'],clearance_mm=58-h,
                         solid_mass_upper_bound_g=used['self_mass_solid_upper_bound_g'],
                         three_60g_E1000_mm=scenario(used,60,'three_cars'),
                         three_100g_E1000_mm=scenario(used,100,'three_cars'),
                         centre_300g_E1000_mm=scenario(used,100,'all_payload_at_centre'),
                         centre_600g_E500_mm=2*scenario(used,200,'all_payload_at_centre')))
    limit=.5
    feasible=[r['rib_height_mm'] for r in rows if r['centre_600g_E500_mm']<=limit]
    summary=dict(status='passed',rows=rows,convergence=convergence,
                 selected_deflection_limit_mm=limit,criterion_type='chosen appearance/serviceability target, not a standard or load rating',
                 minimum_tested_rib_height_meeting_sensitivity_case_mm=min(feasible),
                 E1000_and_E500_are_assumptions=True,creep_lifetime_not_predicted=True,
                 CAD_model_modified=False,CAD_sha256=fine['model_sha256'],
                 analysis_source=str(model.relative_to(ROOT)),
                 CAD_model_modified_scope='frozen reference during analysis; production application recorded separately')
    (ROOT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
    with (ROOT/'comparison.csv').open('w') as out:
        writer=csv.DictWriter(out,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(2,2,figsize=(13,9),constrained_layout=True)
    ax=axes[0,0];hs=[r['rib_height_mm'] for r in rows]
    for key,label,color in [('three_60g_E1000_mm','3 x 60 g, wheel contacts, E=1000 MPa','#238b45'),('centre_300g_E1000_mm','300 g at centre, E=1000 MPa','#2878b5'),('centre_600g_E500_mm','600 g at centre, E=500 MPa','#d97822')]:
        ax.plot(hs,[r[key] for r in rows],'o-',color=color,label=label,lw=2)
    ax.axhline(limit,color='#9a3440',ls='--',lw=1,label='Chosen limit: 0.5 mm')
    ax.set(xlabel='Rib height below 5 mm deck [mm]',ylabel='Maximum downward displacement [mm]',ylim=(0,.55),xticks=hs,title='A. Rib height sensitivity (self-weight included)')
    ax.legend(fontsize=8,loc='upper right');ax.grid(alpha=.2)
    ax=axes[0,1];ax.add_patch(Rectangle((0,0),199.6,158.6,facecolor='#f3f4f5',edgecolor='#555'))
    for y in (25.8,124.8):ax.add_patch(Rectangle((25.8,y),148,8,facecolor='#e6a34a',alpha=.6))
    centres=[(13.8,13.8),(185.8,13.8),(13.8,144.8),(185.8,144.8)]
    for x,y in centres:
        ax.add_patch(Circle((x,y),10,facecolor='#cfe2f3',edgecolor='#2878b5'))
        ax.add_patch(Circle((x,y),3.25,facecolor='white',edgecolor='#2878b5'))
    for cx in (50,99.8,149.6):
        for dx in (-10,10):
            for dy in (-20,20):ax.add_patch(Circle((cx+dx,79.3+dy),4,facecolor='#b83d3d',alpha=.8))
    ax.set(xlim=(-8,208),ylim=(-8,166),aspect='equal',xlabel='X [mm]',ylabel='Y [mm]',title='B. Support / load layout + compared rib positions')
    ax.text(99.8,-3,'Collar centres: 172 x 131 mm',ha='center',va='top',fontsize=8)
    ax.text(99.8,164,'Blue: collar supports | Red: wheel-load patches | Orange: optional ribs (h>0)',ha='center',fontsize=8)
    for ax,h in zip(axes[1],(0,8)):
        with gzip.open(ROOT/f'field-h{h}-mesh4.json.gz','rt') as inp:field=json.load(inp)
        xyz=np.array(field['xyz']);u=np.array(field['self_uz_mm'])+3*.1*9.81*np.array(field['cars_1N_uz_mm'])
        top=np.abs(xyz[:,2]-5)<1e-5
        contours=ax.tricontourf(xyz[top,0],xyz[top,1],np.maximum(0,-u[top]),levels=np.linspace(0,.07,22),cmap='viridis',vmin=0,vmax=.07)
        for x,y in centres:
            ax.add_patch(Circle((x,y),3.25,facecolor='white',edgecolor='white'))
        ax.set(xlim=(0,199.6),ylim=(0,158.6),aspect='equal',xlabel='X [mm]',ylabel='Y [mm]',title=f'{"C" if h==0 else "D"}. h={h} mm, 3 x 100 g + self-weight\nE=1000 MPa; max={-u.min():.3f} mm')
        bar=fig.colorbar(contours,ax=ax,shrink=.8);bar.set_label('Downward displacement [mm]')
    fig.suptitle('Parking deck bending study | 199.6 x 158.6 x 5 mm | quadratic solid FEA | selected h=0',fontsize=15,fontweight='bold')
    fig.savefig(ROOT/'bending-comparison.png',dpi=180)
    plt.close(fig)
    print(json.dumps({'minimum_rib_height_mm':min(feasible),'max_mesh_difference_percent':100*max(x['relative_difference'] for x in convergence),'table':rows},indent=2))

if __name__=='__main__':main()
