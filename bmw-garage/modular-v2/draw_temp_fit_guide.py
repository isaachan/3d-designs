"""Illustrated assembly guide for the temporary white P3/P4 test kit."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch
from matplotlib.font_manager import FontProperties

OUT = Path(__file__).resolve().parent / 'generated' / 'temp-fit-review'
FONT = FontProperties(fname='/System/Library/Fonts/Supplemental/Arial Unicode.ttf')
plt.rcParams['svg.fonttype'] = 'path'
fig, axs = plt.subplots(2, 2, figsize=(18, 17))
fig.patch.set_facecolor('#f3f6fa')
INK, BLUE, RED, GRAY = '#203047', '#087bb8', '#cf4939', '#d7dfe8'


def txt(ax, x, y, s, size=13, color=INK, **kw):
    ax.text(x, y, s, fontproperties=FONT, fontsize=size, color=color,
            va='top', **kw)


def rect(ax, x, y, w, h, fill=GRAY, edge=INK, **kw):
    ax.add_patch(Rectangle((x, y), w, h, facecolor=fill, edgecolor=edge,
                           linewidth=1.5, **kw))


def arrow(ax, a, b, color=BLUE, both=False):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle='<->' if both else '-|>',
                                mutation_scale=16, linewidth=2, color=color))


for ax in axs.flat:
    ax.set(xlim=(0, 120), ylim=(0, 120))
    ax.set_aspect('equal'); ax.axis('off')
    rect(ax, 0, 0, 120, 120, 'white', '#d7dfe8')
fig.text(.05, .97, '盘3 / 盘4 · 白色测试件安装图解', fontproperties=FONT,
         fontsize=28, color=INK, va='top')
fig.text(.05, .937, '对应 P3-P4-Fit-Review-TEMP.3mf｜3张测试盘，19件｜示意非等比例，标注尺寸为准',
         fontproperties=FONT, fontsize=14, color=INK)

ax = axs[0, 0]
txt(ax, 5, 115, '① 测试盘1：先选间隙', 20)
txt(ax, 5, 105, '每列配成两对；公件尺寸相同，只有母件间隙不同。', 12)
for x, gap in zip([34, 66, 98], ['0.20', '0.30', '0.40']):
    txt(ax, x, 95, gap+' mm', 13, BLUE, ha='center')
    # Peg, socket, panel, rail in the same front-to-back order as the 3MF.
    rect(ax, x-8, 77, 16, 2)
    rect(ax, x-4, 79, 8, 6)
    rect(ax, x-9, 59, 18, 9)
    rect(ax, x-4, 59, 8, 5, 'white')
    arrow(ax, (x, 75), (x, 69))
    rect(ax, x-9, 44, 18, 2)
    rect(ax, x-9, 26, 18, 8)
    rect(ax, x-2, 29, 4, 5, 'white')
    arrow(ax, (x, 42), (x, 35))
for y, label in [(83,'插脚'), (66,'插孔'), (47,'小隔板'), (32,'导槽')]:
    txt(ax, 4, y, label, 12)
txt(ax, 5, 20, '图上方＝打印盘后方；下方＝前方。数值为单边间隙。\n零件无刻字，取下前标记。先测轻推进入、晃动和拔出力。\n此处外形为识别示意，箭头表示配对，不表示打印朝向。', 11)

ax = axs[0, 1]
txt(ax, 5, 115, '② 测试盘2：粘好隔板测试架', 20)
txt(ax, 5, 104, '侧视图：前方在左，后方在右；屋顶件需翻正。', 12)
# Exploded upper C-shaped part; rail below roof, rear wall downward.
rect(ax, 25, 80, 63, 6)
rect(ax, 85, 42, 3, 38)
rect(ax, 25, 78, 57, 2, '#aebdce')
txt(ax, 25, 94, '屋顶＋后墙（一体件）', 13)
rect(ax, 23.5, 27, 66, 3)
rect(ax, 25, 30, 57, 2, '#aebdce')
txt(ax, 24, 23, '底板条：导槽朝上', 12)
arrow(ax, (86.5, 41), (86.5, 32))
rect(ax, 85, 30, 3, .8, RED, RED)
arrow(ax, (111, 49), (87, 31), RED)
txt(ax, 94, 64, '仅此处\n可点胶', 12, RED)
# Explicit inset dimension callout rather than exaggerated unlabelled geometry.
arrow(ax, (88, 25), (89.5, 25), both=True)
txt(ax, 69, 20, '后墙外侧距底板后缘 2 mm', 11)
txt(ax, 5, 13, '左右边缘对齐，上下槽居中；后墙垂直、屋顶平行。\n胶不能进入导槽。待胶固化再插隔板，操作时扶住底座。', 11)

ax = axs[1, 0]
txt(ax, 5, 115, '③ 全尺寸隔板：前推装入、前抽拆下', 19)
txt(ax, 5, 104, '侧视示意；上下槽接纳板边，隔板本身禁止胶粘。', 12)
rect(ax, 43, 75, 64, 6)
rect(ax, 104, 27, 3, 48)
rect(ax, 41.5, 24, 67, 3)
rect(ax, 43, 27, 58, 2, '#aebdce')
rect(ax, 43, 73, 58, 2, '#aebdce')
# Partially withdrawn panel. Cyan is an illustrative overlay, not filament.
rect(ax, 20, 28, 56, 46, '#e8f5fc', BLUE)
rect(ax, 17, 33, 3, 7, '#e8f5fc', BLUE)
txt(ax, 25, 60, '隔板\n（部分抽出）', 12, BLUE)
arrow(ax, (13, 86), (63, 86)); txt(ax, 16, 96, '装入：向后推至止挡', 12, BLUE)
arrow(ax, (69, 18), (12, 18)); txt(ax, 22, 15, '拆下：向前抽约82 mm', 12, BLUE)
arrow(ax, (10, 43), (10, 69)); txt(ax, 3, 80, '脱轨后\n再上提', 11, BLUE)
txt(ax, 5, 8, '勿在槽内硬拔上提。检查全程卡滞、翘曲及晃动。', 11)

ax = axs[1, 1]
txt(ax, 5, 115, '④ 测试盘3：招牌双脚同时入孔', 20)
txt(ax, 5, 104, '俯视示意：孔口朝前、插脚水平，勿孔口朝上测试。', 12)
# Plan view, fascia lies in X and pegs extend rearward.
rect(ax, 13, 77, 94, 9)
for x in [19, 97]:
    rect(ax, x-2.4, 77, 4.8, 5.5, 'white')
rect(ax, 14, 51, 92, 3, '#e8f5fc', BLUE)
for x in [19, 97]:
    rect(ax, x-2, 54, 4, 6, '#e8f5fc', BLUE)
    arrow(ax, (x, 63), (x, 75))
txt(ax, 38, 94, '固定或扶住插孔梁', 13)
txt(ax, 40, 70, '背面推至贴靠', 12, BLUE)
txt(ax, 31, 47, '门头长200 mm；双脚间距184 mm', 11)
arrow(ax, (10, 76), (10, 57), both=True)
txt(ax, 4, 42, '两种招牌都要测：内侧招牌双脚间距32 mm。\n招牌、插脚及插孔内均不涂胶；插孔梁可粘辅助支架。', 12)
txt(ax, 5, 27, '检查：双脚同时对位 → 背面贴靠 → 轻触不滑脱\n          → 徒手可拔出 → 插拔20次后无明显变松', 12, BLUE)
txt(ax, 5, 12, '全尺寸件与插孔梁固定用0.30 mm间隙；\n若小样选了其他间隙，需改模型重测，不能整体缩放。', 11)

fig.text(.05, .037, '测试记录：材料 / 层高 / 间隙 / 是否卡滞 / 晃动 / 插拔20次前后变化。尚未实物验证。',
         fontproperties=FONT, fontsize=13, color=INK)
fig.text(.05, .016, '图中蓝色＝可拆测试件或动作，红色＝允许胶粘位置；实际全部为白色。测试架不模拟整座建筑翘曲。',
         fontproperties=FONT, fontsize=12, color=INK)
fig.subplots_adjust(left=.04, right=.98, top=.905, bottom=.06, wspace=.08, hspace=.07)
for ext in ['png', 'pdf']:
    fig.savefig(OUT / f'assembly-guide.{ext}', dpi=180, facecolor=fig.get_facecolor())
print(OUT / 'assembly-guide.png')
