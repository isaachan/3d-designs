from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
fig,ax=plt.subplots(figsize=(10,5));ax.add_patch(Polygon([(-7,0),(-1.608,0),(-3.2,1.9),(3.2,1.9),(1.608,0),(7,0),(7,4),(-7,4)],facecolor='#999fa8',edgecolor='#303840',lw=2))
ax.add_patch(Polygon([(-7,-2),(7,-2),(7,-.2),(1.108,-.2),(2.6,1.6),(-2.6,1.6),(-1.108,-.2),(-7,-.2)],facecolor='#2863c6',edgecolor='#123d78',lw=2))
ax.text(0,3,'FIXED RECEIVER',ha='center',weight='bold');ax.text(0,-1.3,'REPLACEABLE TEXT PLATE',color='white',ha='center',weight='bold')
ax.annotate('Wider inside: captures the rail',xy=(2.7,1.4),xytext=(0,5.2),ha='center',arrowprops={'arrowstyle':'->'})
ax.text(0,-3.0,'Slide perpendicular to this section. Pull the locking pin before sliding.',ha='center')
ax.text(0,-3.8,'Groove depth 1.9 mm | Rail depth 1.6 mm | Side clearance ~0.33 mm',ha='center',color='#4b5563')
ax.set_xlim(-8.5,8.5);ax.set_ylim(-4.5,6);ax.set_aspect('equal');ax.axis('off');fig.tight_layout();fig.savefig(Path(__file__).resolve().parent/'reports/interface-section.png',dpi=170)
