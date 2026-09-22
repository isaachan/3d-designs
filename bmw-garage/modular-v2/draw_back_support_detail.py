from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch, Polygon
from matplotlib.font_manager import FontProperties

OUT = Path(__file__).resolve().parent / 'generated' / 'temp-fit-review'
FONT = FontProperties(fname='/System/Library/Fonts/Supplemental/Arial Unicode.ttf')
plt.rcParams['svg.fonttype'] = 'path'
plt.rcParams['path.sketch'] = (1, 90, 1.5)

fig, axs = plt.subplots(2, 3, figsize=(18, 12))
fig.patch.set_facecolor('#f6f3ea')
INK='#263238'; BLUE='#1976a3'; RED='#c44135'; GREEN='#5f8d3a'; GREY='#d7dfe7'; DARK='#9aa8b3'; PAPER='#fffdf7'; YELLOW='#f4d06f'


def txt(ax,x,y,s,size=12,color=INK,**kw):
    ax.text(x,y,s,fontproperties=FONT,fontsize=size,color=color,va='top',**kw)

def rect(ax,x,y,w,h,fc=GREY,ec=INK,lw=1.8,**kw):
    p=Rectangle((x,y),w,h,facecolor=fc,edgecolor=ec,linewidth=lw,**kw); ax.add_patch(p); return p

def poly(ax,pts,fc=GREY,ec=INK,lw=1.8,**kw):
    p=Polygon(pts,closed=True,facecolor=fc,edgecolor=ec,linewidth=lw,**kw); ax.add_patch(p); return p

def arrow(ax,a,b,color=BLUE,lw=2.3,style='-|>'):
    ax.add_patch(FancyArrowPatch(a,b,arrowstyle=style,mutation_scale=16,linewidth=lw,color=color))

def setup(ax,title):
    ax.set(xlim=(0,100),ylim=(0,100)); ax.set_aspect('equal'); ax.axis('off')
    rect(ax,1,1,98,98,PAPER,'#d0c8b8',1.2)
    txt(ax,5,95,title,17)

for ax,t in zip(axs.flat,[
    '① 3D位置：门头在前方，剖面切在插脚中心',
    '② 原结构侧剖：只有插脚定位',
    '③ 加台阶侧剖：主体上增加贴靠面',
    '④ 推到底：面板背面压在台阶上',
    '⑤ 为什么能贴平：台阶承担抗翘',
    '⑥ 设计边界：避开插脚，不堵抽换路径'
]): setup(ax,t)

fig.text(.04,.985,'背面支撑台阶：从3D位置到剖面细节',fontproperties=FONT,fontsize=25,color=INK,va='top')
fig.text(.04,.952,'目的：解决长门头招牌背面不贴平、轻碰后翘/歪的问题；它配合0.20插孔和摩擦筋使用。',fontproperties=FONT,fontsize=13,color=INK)

# 1 3D-ish view with cut plane
ax=axs[0,0]
# body roof/wall isometric
poly(ax,[(12,30),(78,30),(88,40),(22,40)],GREY)
poly(ax,[(78,30),(88,40),(88,73),(78,63)],DARK)
poly(ax,[(12,30),(22,40),(22,73),(12,63)],DARK)
poly(ax,[(12,63),(78,63),(88,73),(22,73)],'#c8d2db')
# sign board front
poly(ax,[(18,18),(82,18),(88,23),(24,23)],'#e8f5fc',BLUE,2.2)
# pegs
poly(ax,[(31,23),(38,23),(42,30),(35,30)],'#e8f5fc',BLUE,1.6)
poly(ax,[(63,23),(70,23),(74,30),(67,30)],'#e8f5fc',BLUE,1.6)
# cut plane translucent rectangle line at right peg center
poly(ax,[(66,12),(72,15),(72,82),(66,78)],YELLOW,RED,2,alpha=.45)
txt(ax,62,88,'剖面A-A：\n穿过插脚中心',12,RED)
arrow(ax,(65,83),(68,70),RED)
txt(ax,8,12,'看剖面时：左右方向被省略，\n只看“招牌—插脚—主体”的前后关系。',11)

# 2 Original side section
ax=axs[0,1]
# coordinate front left, rear right
rect(ax,18,22,62,8,GREY)
rect(ax,72,30,8,45,GREY)
# socket hole
rect(ax,41,30,14,17,PAPER,INK,1.6)
# sign floating/slightly tilted
poly(ax,[(15,51),(70,47),(70,55),(15,59)],'#e8f5fc',BLUE,2)
poly(ax,[(43,45),(55,45),(55,51),(43,51)],'#e8f5fc',BLUE,2)
# gap callouts
arrow(ax,(36,49),(36,39),RED); arrow(ax,(67,49),(67,43),RED)
txt(ax,8,84,'没有连续贴靠面：',13,RED)
txt(ax,8,75,'两个插脚一松，长面板\n就容易绕插脚前后转。',12)
txt(ax,20,13,'结果：背面不贴平，轻碰会翘/滑出。',12,RED)

# 3 Added support ledge section
ax=axs[0,2]
rect(ax,18,22,62,8,GREY)
rect(ax,72,30,8,45,GREY)
rect(ax,32,45,40,7,'#bfd0bc',GREEN,2.5)
rect(ax,41,30,14,17,PAPER,INK,1.6)
# ledge chamfer/entry relief
poly(ax,[(28,45),(32,45),(32,52)],'#bfd0bc',GREEN,2.0)
txt(ax,40,68,'新增/加强\n背面支撑台阶',13,GREEN,ha='center')
arrow(ax,(50,63),(52,52),GREEN)
txt(ax,7,82,'台阶位置：',13,GREEN)
txt(ax,7,73,'在主体/屋顶承接面上，\n不是做在可换招牌上。',12)
txt(ax,8,13,'中间留出插孔；前端可做小倒角，方便推入。',11)

# 4 Contact after pushed in
ax=axs[1,0]
rect(ax,18,22,62,8,GREY)
rect(ax,72,30,8,45,GREY)
rect(ax,32,45,40,7,'#bfd0bc',GREEN,2.5)
rect(ax,41,30,14,17,PAPER,INK,1.3)
rect(ax,16,52,56,7,'#e8f5fc',BLUE,2.3)
rect(ax,43,45,12,7,'#e8f5fc',BLUE,2.0)
# contact hatch
for x in [34,40,46,52,58,64,70]:
    ax.plot([x,x+3],[52.2,55.5],color=GREEN,lw=2)
arrow(ax,(8,55),(16,55),BLUE)
txt(ax,7,82,'推到底后的状态：',13,BLUE)
txt(ax,7,73,'招牌背面整条压住台阶，\n插脚只负责定位/抗拔。',12)
txt(ax,18,14,'绿色斜线＝实际贴靠区域。',12,GREEN)

# 5 Force/anti tilt
ax=axs[1,1]
rect(ax,18,22,62,8,GREY)
rect(ax,72,30,8,45,GREY)
rect(ax,32,45,40,7,'#bfd0bc',GREEN,2.5)
rect(ax,16,52,56,7,'#e8f5fc',BLUE,2.3)
rect(ax,43,45,12,7,'#e8f5fc',BLUE,2.0)
# force arrows
arrow(ax,(29,70),(29,58),RED); txt(ax,10,78,'手碰门头\n产生翻转力',12,RED)
arrow(ax,(61,44),(61,52),GREEN); txt(ax,66,48,'台阶反力\n阻止后翘',12,GREEN)
arrow(ax,(49,39),(49,45),BLUE); txt(ax,19,39,'插脚定位',12,BLUE)
txt(ax,8,16,'没有台阶时，这个力矩主要由两个小插脚承担；\n加台阶后，长面板靠面受力，姿态稳定得多。',11)

# 6 Design boundary top/section note
ax=axs[1,2]
# front view/top-ish beam
rect(ax,10,58,80,14,GREY)
# sockets
rect(ax,20,61,8,8,PAPER,INK,1.5); rect(ax,72,61,8,8,PAPER,INK,1.5)
# support ledge strip behind/under, interrupted around sockets
rect(ax,12,47,76,6,'#bfd0bc',GREEN,2.2)
rect(ax,18,47,12,6,PAPER,PAPER,0)
rect(ax,70,47,12,6,PAPER,PAPER,0)
# sign outline
rect(ax,8,36,84,5,'#e8f5fc',BLUE,2)
arrow(ax,(50,34),(50,46),BLUE)
txt(ax,34,31,'招牌推入方向',12,BLUE)
txt(ax,8,85,'从正面看/俯视：',13)
txt(ax,8,78,'台阶可做成长条，但要避开插孔入口，\n不能挡住插脚插入和拔出。',12)
txt(ax,8,20,'建议：门头优先加连续贴靠面；插孔间隙改0.20；\n再在插脚侧面加浅摩擦筋解决滑出。',11)

fig.text(.04,.035,'注：图为结构示意，比例经过夸张；实际尺寸需按现有门头厚度、插孔深度和打印余量建模，并重新打印门头测试件验证。',fontproperties=FONT,fontsize=12,color=INK)
fig.subplots_adjust(left=.035,right=.985,top=.905,bottom=.07,wspace=.06,hspace=.1)
fig.savefig(OUT/'back-support-detail.png',dpi=180,facecolor=fig.get_facecolor())
fig.savefig(OUT/'back-support-detail.pdf',dpi=180,facecolor=fig.get_facecolor())
print(OUT/'back-support-detail.png')
