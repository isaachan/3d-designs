import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
OUT=Path(__file__).resolve().parent
data=json.loads((OUT/'package-and-topology.json').read_text())
fig,axs=plt.subplots(1,2,figsize=(13,6))
for ax in axs:
    ax.add_patch(Rectangle((0,0),200,200,facecolor='#e3f1e9',edgecolor='#2c7755',linewidth=2))
    ax.text(8,185,'Saved bed: 200 x 200 mm',fontsize=10,color='#245c44')
    ax.set_aspect('equal');ax.set_xlabel('X / mm');ax.set_ylabel('Y / mm');ax.grid(alpha=.15)
for i in data['projects'][0]['items']:
    if i['name'] not in ['01_base_01.stl','01_base_02.stl','01_base_03.stl']:continue
    (x,y,z),(xx,yy,zz)=i['bounds']
    axs[0].add_patch(Rectangle((x,y),xx-x,yy-y,facecolor='#ee9655',alpha=.25,edgecolor='#a1491c',lw=1.5))
axs[0].text(130,-110,'Base 01 / 02 / 03\nsame bounding box\nand overlapping bodies',fontsize=10)
axs[0].set(xlim=(-20,380),ylim=(-180,220),title='Grey project: three bases assigned to plate 1')
for i in data['projects'][4]['items']:
    (x,y,z),(xx,yy,zz)=i['bounds']
    c='#df764b' if i['plate'] is None else '#5683bc'
    axs[1].add_patch(Rectangle((x,y),xx-x,yy-y,facecolor=c,alpha=.8))
axs[1].text(225,15,'309 mm title: outside bed,\nnot assigned to a plate',fontsize=10,color='#a14425')
axs[1].set(xlim=(-20,550),ylim=(-50,250),title='White project: title will not print from plate 1')
fig.suptitle('Actual 3MF build positions (bounding boxes; no automatic rearrangement)',fontsize=14)
fig.tight_layout();fig.savefig(OUT/'saved-print-layout.png',dpi=160)
