#!/usr/bin/env python3
"""Draw the concept's continuous route as a native SVG (not a CAD model)."""
import math
from pathlib import Path
from html import escape

ROOT = Path(__file__).resolve().parent
TAU = math.tau
PITCH, RADIUS, ROAD_WIDTH = 63.0, 120.0, 70.0
CX, CY = 395.0, 65.0
SCALE_X, SCALE_Y = 1.45, 1.05
COLORS = ["#39A9DB", "#5059B5", "#ED242A"]
parts, faces = [], []


def p(x, y, z):
    return (145 + SCALE_X * (x + 0.38 * y),
            695 + SCALE_Y * (0.25 * x - 0.45 * y - 1.55 * z))


def pts(points):
    return " ".join(f"{x:.2f},{y:.2f}" for x, y in points)


def polygon(points, fill, stroke="#26333D", width=0.7):
    return f'<polygon points="{pts(points)}" fill="{fill}" stroke="{stroke}" stroke-width="{width}" stroke-linejoin="round"/>'


def face(vertices, fill):
    depth = sum(y - 0.38 * x - 0.35 * z for x, y, z in vertices) / len(vertices)
    faces.append((depth, polygon([p(*v) for v in vertices], fill)))


def path(points, stroke, width=2, dash="", opacity=1):
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<polyline points="{pts(points)}" fill="none" stroke="{stroke}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round" opacity="{opacity}"{dash_attr}/>'


def text(x, y, value, size=20, color="#263541", weight=400, extra=""):
    return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{color}" {extra}>{escape(value)}</text>'


def rise(u):
    """30-degree total flat landing plus 15-degree cosine slope transitions."""
    landing = math.radians(15)
    easing = math.radians(15)
    a, b = landing, TAU - landing
    run = b - a
    effective_run = run - easing
    t = u * TAU - a
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
        tail = q / 2 - easing * math.sin(math.pi * q / easing) / (2 * math.pi)
        integral = effective_run - tail
    return integral / effective_run


def xyz(turn, u, radius=RADIUS):
    angle = math.pi + TAU * u
    return (CX + radius * math.cos(angle), CY + radius * math.sin(angle),
            8 + PITCH * (turn + rise(u)))


parts.append('<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1120" viewBox="0 0 1600 1120">')
parts.append('<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0 0 L6 3 L0 6" fill="none" stroke="#39A9DB" stroke-width="1.5"/></marker></defs>')
parts.append('<rect width="1600" height="1120" fill="#F5F4EF"/>')
parts.append('<g font-family="PingFang SC, Noto Sans CJK SC, Microsoft YaHei, sans-serif">')
parts.append(text(72, 75, "PARKING LOT / CONCEPT 01", 17, "#64747E", 600, 'letter-spacing="3"'))
parts.append(text(72, 132, "四层停车场 · 连续螺旋通行", 40, "#18262F", 600))
parts.append(text(72, 172, "沿用 garage 的停车楼与装饰，侧置三圈坡道，逐层平接。", 21, "#64747E"))
parts.append('<rect x="64" y="211" width="1088" height="637" rx="22" fill="#FFFFFF"/>')
parts.append('<rect x="1176" y="211" width="360" height="637" rx="22" fill="#EAEDE9"/>')
parts.append(text(94, 252, "01 / 路线透视示意", 19, "#64747E", 500))

# Four slabs, with the front aisle enlarged relative to the source garage.
for level, bays in enumerate((2, 2, 3, 3)):
    z = 8 + PITCH * level
    edge = "#222C33" if level == 0 else COLORS[level - 1]
    face([(0, 0, z), (200, 0, z), (200, 220, z), (0, 220, z)], "#242E35")
    face([(0, 0, z - 6.6), (200, 0, z - 6.6), (200, 0, z), (0, 0, z)], edge)
    face([(200, 0, z - 6.6), (200, 220, z - 6.6), (200, 220, z), (200, 0, z)], edge)
    # A 70-mm-wide connector joins the widened aisle to each flat landing.
    face([(200, 30, z), (278, 30, z), (278, 100, z), (200, 100, z)], "#34434D")
    for bay in range(bays):
        x0 = 18 + bay * 164 / bays
        x1 = 18 + (bay + 1) * 164 / bays - 7
        for va, vb in [((x0, 118, z + .1), (x0, 207, z + .1)),
                       ((x0, 207, z + .1), (x1, 207, z + .1)),
                       ((x1, 207, z + .1), (x1, 118, z + .1))]:
            depth = sum(v[1] - .38 * v[0] - .35 * v[2] for v in (va, vb)) / 2
            faces.append((depth - .01, path([p(*va), p(*vb)], "#DDE5E7", 1.3)))

# Three genuinely ascending annular surfaces. All four junctions share the
# same angle and elevation as their matching parking slab.
for turn in range(3):
    for i in range(180):
        u0, u1 = i / 180, (i + 1) / 180
        inner0, inner1 = xyz(turn, u0, 85), xyz(turn, u1, 85)
        outer0, outer1 = xyz(turn, u0, 155), xyz(turn, u1, 155)
        face([inner0, outer0, outer1, inner1], "#26343D")
        # Low outside rim and underside edge.
        face([outer0, outer1, (outer1[0], outer1[1], outer1[2] - 5),
              (outer0[0], outer0[1], outer0[2] - 5)], COLORS[turn])

parts.extend(markup for _, markup in sorted(faces, reverse=True, key=lambda item: item[0]))

# The colored centerline is intentionally drawn as a transparent route overlay.
for turn in range(3):
    for half in range(2):
        us = [(half + i / 100) / 2 for i in range(101)]
        route = [p(*xyz(turn, u)) for u in us]
        parts.append(path(route, "#FFFFFF", 7, opacity=.93))
        parts.append(path(route, COLORS[turn], 4, "8 7" if half else ""))
    for u in (.21, .71):
        route = [p(*xyz(turn, u - .015)), p(*xyz(turn, u + .015))]
        parts.append(path(route, "#FFFFFF", 2.2)[:-2] + ' marker-end="url(#arrow)"/>')

for level in range(4):
    z = 8 + PITCH * level
    a, b = p(155, 65, z + .5), p(275, 65, z + .5)
    parts.append(path([a, b], "#F4F7F8", 4))
    node = p(275, 65, z + .5)
    parts.append(f'<circle cx="{node[0]:.2f}" cy="{node[1]:.2f}" r="9" fill="#FFFFFF" stroke="#39A9DB" stroke-width="3"/>')
    label = p(-14, 0, z)
    parts.append(text(round(label[0]) - 30, round(label[1]) + 6, f"{level + 1}F", 24, "#18262F", 700))

parts.append(text(96, 814, "实线 / 虚线区分前后半圈；彩色线为路线叠加示意。", 17, "#64747E"))
parts.append(text(1206, 260, "从一层开到四层", 25, "#18262F", 600))
parts.append(text(1206, 294, "同一条连续道路 · 每层可驶入", 17, "#64747E"))
for i, (floor, label) in enumerate([(4, "开放式顶层 / 坡道终点"),
                                   (3, "平接 3F / 继续上行"),
                                   (2, "平接 2F / 继续上行"),
                                   (1, "首层入口 / 坡道起点")]):
    y = 359 + i * 105
    parts.append(f'<circle cx="1230" cy="{y}" r="23" fill="#18262F"/>')
    parts.append(text(1230, y + 7, f"{floor}", 21, "#FFFFFF", 600, 'text-anchor="middle"'))
    parts.append(text(1270, y - 4, f"{floor}F", 24, "#18262F", 600))
    parts.append(text(1270, y + 24, label, 16, "#64747E"))
    if i < 3:
        parts.append(f'<path d="M1230 {y + 76} L1230 {y + 38}" stroke="{COLORS[2-i]}" stroke-width="4" fill="none"/>')
        parts.append(f'<path d="M1224 {y + 46} L1230 {y + 38} L1236 {y + 46}" stroke="{COLORS[2-i]}" stroke-width="3" fill="none"/>')
parts.append(text(1206, 794, "三圈上升，对应三次跨层。", 18, "#263541", 500))

cards = [(64, "继承", ["黑色圆柱与四层停车板", "顶部广告牌、侧面口号牌", "浅蓝 / 深蓝 / 红收边及白标线"]),
         (562, "新增", ["独立侧置螺旋坡道与低护边", "四处水平接入口，连接前方通道", "加深转向区，避开固定柱位"]),
         (1060, "概念尺度起点", ["层距 63 mm · 路宽 70 mm", "中心半径 120 mm · 外径 310 mm", "含平接与缓坡段，最大纵坡约 9.6%"])]
for x, title, lines in cards:
    parts.append(f'<rect x="{x}" y="876" width="476" height="166" rx="18" fill="#FFFFFF"/>')
    parts.append(text(x + 24, 912, title, 22, "#18262F", 600))
    for j, line in enumerate(lines):
        parts.append(text(x + 24, 947 + j * 31, line, 18, "#64747E"))
parts.append(text(72, 1082, "概念比例，非生产图。下一阶段按实车尺寸校核转向包络、坡道净空、过渡与拆件。", 17, "#64747E"))
parts.append('</g></svg>')
(ROOT / '02-route-diagram.svg').write_text("\n".join(parts), encoding='utf-8')

# Verify the mathematical centerline, rather than treating the AI render as CAD.
samples = [xyz(turn, i / 360) for turn in range(3) for i in range(361)]
assert all(b[2] >= a[2] - 1e-9 for a, b in zip(samples, samples[1:]))
for turn in range(2):
    assert max(abs(a - b) for a, b in zip(xyz(turn, 1), xyz(turn + 1, 0))) < 1e-8
assert xyz(0, 0)[2] == 8 and xyz(2, 1)[2] == 197
assert all(abs(xyz(k, 0)[2] - (8 + 63 * k)) < 1e-8 for k in range(3))
max_grade = PITCH / (RADIUS * math.radians(315))
print(f'Wrote {ROOT / "02-route-diagram.svg"}')
print(f'Continuous route: 3 turns, 4 levels, rise 189 mm; max conceptual centerline grade {max_grade:.2%}')
