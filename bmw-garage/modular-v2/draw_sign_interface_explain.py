from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch, Polygon, Circle
from matplotlib.font_manager import FontProperties

OUT = Path(__file__).resolve().parent / 'generated' / 'temp-fit-review'
FONT = FontProperties(fname='/System/Library/Fonts/Supplemental/Arial Unicode.ttf')
plt.rcParams['svg.fonttype'] = 'path'
plt.rcParams['path.sketch'] = (1, 120, 2)  # light hand-drawn feel

fig, axs = plt.subplots(1, 2, figsize=(16, 8))
fig.patch.set_facecolor('#f6f3ea')
INK = '#263238'; BLUE = '#1976a3'; RED = '#c44135'; GREEN = '#5f8d3a'; PAPER = '#fffdf7'; GREY = '#d9e0e6'


def txt(ax, x, y, s, size=14, color=INK, **kw):
    ax.text(x, y, s, fontproperties=FONT, fontsize=size, color=color, va='top', **kw)

def rect(ax, x, y, w, h, fc=GREY, ec=INK, lw=2, **kw):
    p = Rectangle((x, y), w, h, facecolor=fc, edgecolor=ec, linewidth=lw, **kw)
    ax.add_patch(p); return p

def arrow(ax, a, b, color=BLUE, lw=2.5, text=None, textpos=None):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle='-|>', mutation_scale=18, linewidth=lw, color=color))
    if text:
        txt(ax, *(textpos or ((a[0]+b[0])/2, (a[1]+b[1])/2)), text, 13, color)

for ax in axs:
    ax.set(xlim=(0, 100), ylim=(0, 100)); ax.set_aspect('equal'); ax.axis('off')
    rect(ax, 1, 1, 98, 98, PAPER, '#d0c8b8', 1.5)

fig.text(.05, .94, '门头招牌接口：两个建议改法', fontproperties=FONT, fontsize=28, color=INK)
fig.text(.05, .895, '左：背面支撑台阶让长招牌贴平；右：摩擦筋让插脚有阻尼，不轻碰滑出。', fontproperties=FONT, fontsize=15, color=INK)

# Left: side section for rear support ledge
ax = axs[0]
txt(ax, 6, 94, 'A. 背面支撑台阶（侧剖示意）', 19)
txt(ax, 6, 84, '问题：长门头只靠两个插脚，容易前后翘，背面不贴平。', 12)
# body wall/roof receiver
rect(ax, 16, 30, 68, 10, '#cfd8df')
rect(ax, 76, 40, 8, 32, '#cfd8df')
# support ledge face on body
rect(ax, 36, 43, 40, 6, '#b7c5ce', GREEN, 2.5)
txt(ax, 40, 57, '新增/加强的\n贴靠台阶', 13, GREEN, ha='center')
arrow(ax, (56, 56), (56, 49), GREEN)
# sign panel and peg
rect(ax, 20, 49, 56, 7, '#e9f5fb', BLUE, 2.5)
rect(ax, 48, 40, 12, 9, '#e9f5fb', BLUE, 2.5)
txt(ax, 25, 66, '招牌背面推到底后\n压在这条面上', 13, BLUE)
arrow(ax, (74, 63), (62, 54), BLUE)
# contact highlight
for x in [39, 50, 61, 72]:
    ax.plot([x, x+3], [49.5, 53.5], color=GREEN, lw=2)
# anti tilt annotations
arrow(ax, (22, 24), (72, 24), BLUE, text='插脚负责定位，不再单独承担“扶正”', textpos=(15, 20))
txt(ax, 8, 12, '作用：让面板有可靠贴靠基准，解决“不贴平、翘、歪”。\n注意：它不是锁扣，不能单独解决“太松会滑出”。', 12)

# Right: peg cross-section friction ribs
ax = axs[1]
txt(ax, 6, 94, 'B. 摩擦筋（插脚截面示意）', 19)
txt(ax, 6, 84, '问题：插孔间隙够装配，但长门头轻碰会滑出。', 12)
# socket hole block
rect(ax, 20, 26, 60, 48, '#cfd8df')
rect(ax, 35, 36, 30, 28, PAPER, INK, 2)
txt(ax, 67, 65, '插孔', 13)
# peg inserted
rect(ax, 39, 39, 22, 22, '#e9f5fb', BLUE, 2.5)
# friction ribs protrusions
rect(ax, 37.2, 45, 2.2, 10, RED, RED, 1.5)
rect(ax, 60.8, 45, 2.2, 10, RED, RED, 1.5)
txt(ax, 45, 78, '插脚本体', 13, BLUE, ha='center')
arrow(ax, (50, 76), (50, 61), BLUE)
txt(ax, 12, 47, '摩擦筋', 13, RED, ha='right')
arrow(ax, (15, 48), (37.5, 50), RED)
txt(ax, 88, 47, '摩擦筋', 13, RED, ha='left')
arrow(ax, (85, 48), (62.5, 50), RED)
# compression waves/contact marks
for y in [43, 48, 53, 58]:
    ax.plot([35, 37], [y, y+1], color=RED, lw=1.6)
    ax.plot([63, 65], [y+1, y], color=RED, lw=1.6)
# insertion arrow
arrow(ax, (50, 18), (50, 35), BLUE, text='插入时只有局部轻微挤压', textpos=(33, 16))
txt(ax, 7, 12, '作用：增加可控阻尼，解决“太松、轻碰滑出”。\n好处：比整孔缩小安全；太紧时可只轻磨凸筋。', 12)

# combined recommendation strip
fig.text(.05, .06, '推荐组合：0.20 mm 插孔基础间隙 + 背面支撑台阶 + 插脚两侧浅摩擦筋。目标是：能徒手插拔，但轻碰不掉、背面贴平。',
         fontproperties=FONT, fontsize=15, color=INK)

fig.subplots_adjust(left=.04, right=.98, top=.84, bottom=.12, wspace=.06)
fig.savefig(OUT / 'sign-interface-explained.png', dpi=180, facecolor=fig.get_facecolor())
fig.savefig(OUT / 'sign-interface-explained.pdf', dpi=180, facecolor=fig.get_facecolor())
print(OUT / 'sign-interface-explained.png')
