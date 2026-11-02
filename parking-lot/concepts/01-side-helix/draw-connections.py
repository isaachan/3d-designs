#!/usr/bin/env python3
"""Explain the concept's helical connections with centerlines and an unwrap."""
from pathlib import Path
from html import escape
import math

ROOT = Path(__file__).resolve().parent
W, H = 1200, 1640
INK, MUTED, BG = '#1E2D37', '#586B78', '#F4F5F2'
CYAN, BLUE, RED = '#179EC9', '#344F9B', '#DA444C'
COLORS = (CYAN, BLUE, RED)
PARTS = []


def put(s):
    PARTS.append(s)


def text(x, y, value, size=24, color=INK, weight=400, anchor='start'):
    put(f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}">{escape(value)}</text>')


def rect(x, y, w, h, fill, rx=0, stroke='none', sw=1):
    put(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')


def line(points, color, width=4, dash='', arrow=False):
    points = ' '.join(f'{x:.2f},{y:.2f}' for x, y in points)
    extra = f' stroke-dasharray="{dash}"' if dash else ''
    if arrow:
        extra += f' marker-end="url(#{ {CYAN:"cyan", BLUE:"blue", RED:"red", MUTED:"gray"}[color] })"'
    put(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"{extra}/>')


def node(x, y, name, radius=18):
    put(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{radius}" fill="#FFFFFF" stroke="{INK}" stroke-width="3"/>')
    text(x, y + 7, name, 21, INK, 600, 'middle')


def rise(u):
    # Same 15-degree flats / cosine grade transitions as draw-route.py.
    landing = easing = math.radians(15)
    run = math.tau - 2 * landing
    effective = run - easing
    t = u * math.tau - landing
    if t <= 0:
        return 0.0
    if t >= run:
        return 1.0
    if t < easing:
        integral = t / 2 - easing * math.sin(math.pi * t / easing) / (2 * math.pi)
    elif t <= run - easing:
        integral = t - easing / 2
    else:
        q = run - t
        integral = effective - (q / 2 - easing * math.sin(math.pi * q / easing) / (2 * math.pi))
    return integral / effective


def world(turn, u):
    a = math.pi + math.tau * u
    return 120 * math.cos(a), 120 * math.sin(a), 63 * (turn + rise(u))


def project(v):
    x, y, z = v
    return 800 + 1.8 * (x + .1 * y), 760 - .45 * y - 2.1 * z


put(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
put('<title>四层停车场三圈螺旋坡道连接示意</title>')
put('<desc>浅蓝第一圈从 A 一层到 B 二层，深蓝第二圈从 B 二层到 C 三层，红色第三圈从 C 三层到 D 四层。B、C 是同一条路上共享的平接平台，平台侧面连接停车层。</desc>')
put('<defs>')
for name, color in [('cyan', CYAN), ('blue', BLUE), ('red', RED), ('gray', MUTED)]:
    put(f'<marker id="{name}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M1 1 L9 5 L1 9" fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round"/></marker>')
put('</defs>')
rect(0, 0, W, H, BG)
put('<g font-family="PingFang SC, Microsoft YaHei, Noto Sans CJK SC, sans-serif">')
text(60, 69, '三段坡道，接成一条路', 40, INK, 600)
text(60, 110, '每转一圈上升一层：1F → 2F → 3F → 4F', 25, MUTED)
for i, (color, label) in enumerate(zip(COLORS, ['第 1 圈：1F → 2F', '第 2 圈：2F → 3F', '第 3 圈：3F → 4F'])):
    x = 64 + i * 377
    line([(x, 153), (x + 40, 153)], color, 7)
    text(x + 55, 160, label, 23)

# A. Helical centerline, with all obstructing panels and curbs omitted.
rect(42, 190, 1116, 646, '#FFFFFF', 18)
text(70, 232, '① 螺旋状态：A、B、C、D 在同一侧，逐层抬高', 25, INK, 600)
text(70, 270, '仅画道路中心线；省略护栏、立柱，竖向间距放大。', 21, MUTED)

junctions = [project(world(0, 0))] + [project(world(k, 1)) for k in range(3)]
for i, (x, y) in enumerate(junctions):
    rect(82, round(y - 22), 235, 44, '#E9EEF0', 6)
    text(104, y + 8, f'{i + 1}F 停车层', 24, INK, 500)
    line([(317, y), (x - 18, y)], '#A1ADB3', 14)

# Draw only the far semicircles dashed. The full sampled path is continuous.
for turn in range(3):
    back = [project(world(turn, .5 + j / 320)) for j in range(161)]
    line(back, COLORS[turn], 7, '9 9')
for turn in range(3):
    front = [project(world(turn, j / 320)) for j in range(161)]
    line(front, '#FFFFFF', 17)
    line(front, COLORS[turn], 10)
    # Forward direction appears once on each foreground half.
    line([project(world(turn, .27)), project(world(turn, .31))], COLORS[turn], 7, arrow=True)
    line([project(world(turn, .72)), project(world(turn, .76))], COLORS[turn], 5, arrow=True)

for i, (x, y) in enumerate(junctions):
    node(x, y, 'ABCD'[i], 19)
    labels = ['起点', '第 1 圈终点 / 第 2 圈起点', '第 2 圈终点 / 第 3 圈起点', '终点']
    if i in (1, 2):
        text(350, y - 28, '接点 ' + 'ABCD'[i], 22, INK, 600)
        text(350, y + 39, labels[i], 18, MUTED)
    else:
        text(x - 4, y + (41 if i == 0 else -29), labels[i], 21, MUTED, 400, 'middle')
text(72, 807, '实线：前半圈    虚线：后半圈    箭头：上行方向', 21, MUTED)

# B. Unwrap angle versus height. Shared B/C flats make the join explicit.
rect(42, 858, 1116, 426, '#FFFFFF', 18)
text(70, 900, '② 把道路展开：上一圈的终点，就是下一圈的起点', 25, INK, 600)
xs, ys = [135, 445, 755, 1065], [1190, 1110, 1030, 950]
for i in range(3):
    u_points = [(xs[i] + 25 + (xs[i + 1] - xs[i] - 50) * j / 100,
                 ys[i] + (ys[i + 1] - ys[i]) * rise(j / 100)) for j in range(101)]
    line(u_points, COLORS[i], 9)
    j = 47
    line(u_points[j:j + 7], COLORS[i], 6, arrow=True)
    mid_x = (xs[i] + xs[i + 1]) / 2
    mid_y = (ys[i] + ys[i + 1]) / 2
    text(mid_x - 14, mid_y - 22, f'第 {i + 1} 圈', 23, COLORS[i], 500, 'middle')

for i, (x, y) in enumerate(zip(xs, ys)):
    line([(x - 25, y), (x + 25, y)], '#DCE4E7', 19)
    line([(x - 25, y), (x + 25, y)], INK, 4)
    node(x, y, 'ABCD'[i], 16)
    text(x, y - 31, f'{i + 1}F', 24, INK, 600, 'middle')
    if i in (1, 2):
        line([(x, y + 20), (x, y + 65)], MUTED, 3, arrow=True)
        rect(x - 79, y + 76, 158, 37, '#E9EEF0', 5)
        text(x, y + 102, f'{i + 1}F 停车层', 20, INK, 400, 'middle')
text(70, 1254, 'B、C 都是平接段：沿主路继续上行，侧向转入该层停车区。', 22, MUTED)

# C. Shared junction B as a schematic local top view.
rect(42, 1306, 1116, 276, '#FFFFFF', 18)
text(70, 1349, '③ 接点 B 放大：同一块水平平台，接两段坡道和一条停车支路', 24, INK, 600)
rect(470, 1391, 208, 68, '#E9EEF0', 8, '#9BAAB1', 1.5)
line([(150, 1425), (545, 1425)], CYAN, 12, arrow=True)
line([(601, 1425), (1020, 1425)], BLUE, 12, arrow=True)
node(574, 1425, 'B', 18)
text(152, 1392, '第一圈到达 2F', 23, CYAN, 500)
text(820, 1392, '第二圈继续上楼', 23, BLUE, 500)
line([(574, 1446), (574, 1500)], MUTED, 5, arrow=True)
rect(472, 1514, 204, 42, '#E9EEF0', 6)
text(574, 1543, '2F 停车层', 23, INK, 500, 'middle')
text(740, 1515, 'B 点两侧同高、无台阶', 23, INK, 500)
text(740, 1550, 'C 点采用相同连接方式', 22, MUTED)
text(60, 1617, '连接原理示意；几何以通行逻辑为准，后续在 CAD 中落实坡道和平接平台。', 20, MUTED)
put('</g></svg>')

for turn in range(2):
    assert max(abs(a - b) for a, b in zip(world(turn, 1), world(turn + 1, 0))) < 1e-8
for turn in range(3):
    heights = [world(turn, j / 360)[2] for j in range(361)]
    assert all(b >= a - 1e-8 for a, b in zip(heights, heights[1:]))
    assert abs(world(turn, .01)[2] - world(turn, 0)[2]) < 1e-8
    assert abs(world(turn, .99)[2] - world(turn, 1)[2]) < 1e-8
out = ROOT / '06-ramp-connections.svg'
out.write_text('\n'.join(PARTS), encoding='utf-8')
print(f'Wrote {out}')
print('PASS: B/C coincide in 3D; each turn rises 63 mm; endpoint landings are flat.')
