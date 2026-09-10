"""Illustrative segmentation only; does not modify production CAD or meshes."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
OUT=Path(__file__).resolve().parent
fig,ax=plt.subplots(figsize=(13,5.5))
cuts=[0,180,410,590,770,920]
for i,(a,b) in enumerate(zip(cuts,cuts[1:]),1):
    ax.add_patch(Rectangle((a,8),b-a,230,facecolor=['#d9eae1','#c1dccd'][i%2],edgecolor='none'))
    ax.add_patch(Rectangle((a,238),b-a,70,facecolor='#d8e6f5',edgecolor='none'))
    ax.text((a+b)/2,100,f'Module {i}\n{b-a} mm',ha='center',fontsize=12,color='#244f3e')
ax.add_patch(Rectangle((0,0),920,8,facecolor='#5b6773'))
for x in [360,914]:
    ax.add_patch(Rectangle((x,8),6,300,facecolor='#394552'))
for x in cuts[1:-1]:ax.plot([x,x],[0,308],color='#d85343',lw=2)
ax.plot([0,920],[238,238],color='#2d64a1',ls='--',lw=2)
ax.text(470,268,'70 mm upper sections',ha='center',color='#245387',fontsize=12)
ax.annotate('Divider: X = 360–366 mm',xy=(363,180),xytext=(190,355),arrowprops=dict(arrowstyle='->',color='#394552'),fontsize=11)
fig.text(.06,.035,'Example only: depth 220 mm; lower assembly height 238 mm including the 8 mm base.',fontsize=11)
ax.set(xlim=(-15,940),ylim=(-15,375),xlabel='X / mm',ylabel='Height above desk / mm',xticks=cuts,yticks=[0,238,308])
ax.set_aspect('equal');ax.spines[['top','right']].set_visible(False)
fig.suptitle('Concept: preserve integrated roots, split away from the divider',fontsize=16)
fig.subplots_adjust(bottom=.23,top=.87,left=.06,right=.99)
fig.savefig(OUT/'segmentation-concept.png',dpi=170)
