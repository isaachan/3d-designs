"""Render the revised column reuse proposal and export its real local assembly."""
import json
import math
import sys
from pathlib import Path
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent)); sys.path.insert(0, str(ROOT.parent.parent))
import column_parts as m
import build_geometry as b
import draw_installation as d
from PIL import Image, ImageDraw
import numpy as np

ADAPTER = (.49, .37, .21)


def levels_for(deg):
    theta = math.radians(deg)
    while theta < math.pi: theta += math.tau
    return theta, [b.height(theta+k*math.tau) for k in range(3)]


def exploded():
    theta, heights = levels_for(275)
    h = heights[1]
    parts = m.station(theta+math.tau, b.height)
    actors = []
    for p in parts:
        s = p['shape'].copy(); s.translate(m.V(p['explode']))
        a = d.as_actor(s, p['color'])
        if p['role'] == 'road': a.GetProperty().SetOpacity(.32)
        actors.append(a)
    lower = m.garage_segment(m.TAB_BOTTOM-m.SEGMENT_HEIGHT)
    upper = m.garage_segment(m.TAB_TOP)
    lower = lower.common(m.box(-15, 15, -15, 15, -43, 1)); lower.translate(m.V(0, 0, -17))
    upper = upper.common(m.box(-15, 15, -15, 15, -5, 22)); upper.translate(m.V(0, 0, 40))
    actors += [d.as_actor(lower, m.BLACK), d.as_actor(upper, m.BLACK)]
    image, point, win = d.render(actors, (1.0, -2.8, 1.0), (1800, 1120), .77)
    canvas = Image.new('RGB', (1800, 1450), d.PAPER); canvas.paste(image, (0, 145)); pen = ImageDraw.Draw(canvas)
    d.title(canvas, '坡道支撑改版｜直接复用车库分段柱', '下段托环 → 6.6 mm 托臂安装片 → 上段柱；原来的 Ø6 定位销贯穿安装片。')
    def p(v): return point(v)+[0, 145]
    d.note(pen, p((0, 0, 39)), '原车库上段柱\n底孔 Ø6.5，深 3.3 mm', (1330, 200))
    d.note(pen, p((7, 0, -8)), '新增：托臂根部安装片\n厚 6.6 mm，孔 Ø6.5', (1330, 650))
    d.note(pen, p((0, 0, -24)), '复用：原 Ø6 一体销\n穿过安装片后伸出 3 mm', (1330, 1050))
    d.note(pen, p((-9, 0, -30)), '复用：原 Ø20 托环承重\n下方 3 mm 高、45° 锥肩', (70, 1000))
    d.note(pen, p((-24, 0, -28)), '轨道仍由下方固定\n每臂 2 颗 M3×10', (70, 730))
    d.note(pen, p((-40, 0, 22)), '轨道与托臂分开安装\n原柱段不用改孔', (70, 230))
    pen.text((60, 1320), '装配：下段柱 → 套入托臂片 → 插上段柱，逐层叠装；再安装、固定轨道分片。', font=d.ft(26), fill=d.INK)
    pen.text((60, 1380), '黑色柱段从 garage-bookshelf v5 原 CAD 复制；斜托臂为新件，轨道分片接头仍待设计。', font=d.ft(24), fill=d.MUTED)
    canvas.save(ROOT/'17-column-reuse-exploded.png'); win.Finalize()


def layout():
    actors = []; anchors = []
    for i, deg in enumerate([35, 95, 275]):
        theta, hs = levels_for(deg); x = i*88
        for p in m.post_parts(hs):
            s = p['shape'].copy(); s.translate(m.V(x, 0, 0))
            actors.append(d.as_actor(s, ADAPTER if p['role'] == 'post-base' else m.BLACK))
        for k, h in enumerate(hs):
            for p in m.station(theta, b.height):
                if p['role'] not in ('arm',): continue
                s = p['shape'].copy(); s.translate(m.V(x, 0, h)); actors.append(d.as_actor(s, (.15, .53, .66)))
        anchors.append((x, hs))
    image, point, win = d.render(actors, (.1, -2, .65), (1800, 1080), .73)
    canvas = Image.new('RGB', (1800, 1500), d.PAPER); canvas.paste(image, (0, 150)); pen = ImageDraw.Draw(canvas)
    d.title(canvas, '三根坡道柱｜共用中段，只调整底段高度', '每柱：1 个定高底段＋2 个原版标准柱段＋1 个原版封顶段；托臂以蓝色区分。')
    def p(v): return point(v)+[0, 150]
    for i, (x, hs) in enumerate(anchors):
        q = p((x, 0, 0)); pen.text((q[0]-72, q[1]+25), f'B{i+1} · {[35,95,275][i]}°', font=d.ft(28), fill=d.INK)
        top = hs[0]+m.TAB_BOTTOM
        pen.text((q[0]-102, q[1]+72), f'底段高 {top-1.3:.2f} mm', font=d.ft(24), fill=d.MUTED)
    d.note(pen, p((88, 0, anchors[1][1][1]-30)), '黑色中段与封顶段\n采用原 CAD 实体', (1240, 200))
    d.note(pen, p((0, 0, anchors[0][1][0]-20)), '棕色仅作区分：\n3 种定高底段，实际也打印黑色', (70, 1050))
    pen.text((60, 1300), '复用尺寸：柱身 Ø14｜标准柱身高 56.4｜插销长 9.6｜封顶柱高 33 mm。', font=d.ft(26), fill=d.INK)
    pen.text((60, 1360), '相邻承托面：56.4 mm 柱段＋6.6 mm 安装片＝63 mm，匹配每圈道路高差。', font=d.ft(26), fill=d.INK)
    pen.text((60, 1420), '坡道 B：复用 6 个标准段＋3 个封顶段；侧牌 C：复用 3 个标准段＋1 个封顶段，另配垫片。', font=d.ft(24), fill=d.MUTED)
    canvas.save(ROOT/'18-column-reuse-layout.png'); win.Finalize()


def sections():
    theta, _ = levels_for(275)
    arm = next(p['shape'] for p in m.station(theta, b.height) if p['role'] == 'arm')
    low = m.garage_segment(m.TAB_BOTTOM-m.SEGMENT_HEIGHT)
    upper = m.garage_segment(m.TAB_TOP)
    cut = m.box(-13, 13, 0, 13, -27, 10)
    actors = [d.as_actor(s.common(cut), c) for s, c in [(low, m.BLACK), (arm, (.15,.53,.66)), (upper, m.BLACK)]]
    image, point, win = d.render(actors, (.07, -1, .15), (1800, 1070), .70)
    canvas = Image.new('RGB', (1800, 1400), d.PAPER); canvas.paste(image, (0, 150)); pen = ImageDraw.Draw(canvas)
    d.title(canvas, '柱—托臂半剖｜与原车库层板采用相同接口', '蓝色为新增托臂安装片；黑色为原版柱。下段托环承重，定位销穿片后插入上段盲孔。')
    def p(v): return point(v)+[0, 150]
    d.note(pen, p((3.25, 0, -3.4)), '上段原盲孔 Ø6.5\n孔深 3.3 mm', (1190, 270))
    d.note(pen, p((2.4, 0, -3.3)), '原销 Ø6，插入上段 3 mm\n孔底留 0.3 mm', (1200, 1020))
    d.note(pen, p((-7.8, 0, -8.3)), '安装片厚 6.6 mm\n等同原车库层板厚度', (70, 350))
    a, z = p((-10, 0, m.TAB_BOTTOM)), p((-3.25, 0, m.TAB_BOTTOM))
    pen.line([tuple(a), tuple(z)], fill=d.RED, width=6)
    d.note(pen, (a+z)/2, '红线：托环与安装片\n实际接触承托面', (70, 1030), d.RED)
    pen.text((60, 1270), '托臂安装片位于护栏外侧；柱中心半径 169 mm，Ø20 安装片距外护栏名义净距 2 mm。', font=d.ft(25), fill=d.INK)
    pen.text((60, 1330), '圆销沿用原设计；托臂朝向需由轨道两颗螺钉及整圈装配确定，配合与承载仍需试装。', font=d.ft(24), fill=d.MUTED)
    canvas.save(ROOT/'19-column-tab-section.png'); win.Finalize()


def export_and_check():
    report = dict(source_solids_copied_unmodified=True, standard_height_mm=56.4,
                  tab_thickness_mm=6.6, pitch_mm=63, cap_height_mm=33,
                  pin_diameter_mm=6, hole_diameter_mm=6.5,
                  pin_engagement_mm=3, socket_end_gap_mm=.3, outer_curb_clearance_mm=2,
                  external_reuse=dict(standard_segments=9, top_caps=4), stations=[])
    for deg in [35, 95, 275]:
        theta, hs = levels_for(deg); posts = m.post_parts(hs); post = m.upright(hs)
        values = []
        for k, h in enumerate(hs):
            parts = m.station(theta+k*math.tau, b.height)
            values.append(m.interference_checks(parts, post, h))
        overlaps = [posts[i]['shape'].common(posts[j]['shape']).Volume
                    for i in range(len(posts)) for j in range(i)]
        assert max(overlaps) < 1e-5
        report['stations'].append(dict(angle_deg=deg, first_road_height_mm=hs[0],
            foot_body_height_mm=hs[0]+m.TAB_BOTTOM-1.3, collar_top_z_mm=[h+m.TAB_BOTTOM for h in hs],
            column_pair_max_overlap_mm3=max(overlaps), arms=values))
    theta, hs = levels_for(275)
    doc = m.App.newDocument('ParkingLotColumnReuse')
    def add(name, shape, role):
        assert shape.isValid() and len(shape.Solids) == 1, name
        obj = doc.addObject('PartDesign::Feature', name); obj.Shape = shape
        obj.addProperty('App::PropertyString', 'DesignRole'); obj.DesignRole = role
    for p in m.post_parts(hs): add(p['name'], p['shape'], p['role'])
    for k, h in enumerate(hs):
        for p in m.station(theta+k*math.tau, b.height):
            s = p['shape'].copy(); s.translate(m.V(0,0,h)); add(f'level_{k+1}_'+p['name'], s, p['role'])
    for p in m.foot_hardware(): add(p['name'], p['shape'], p['role'])
    doc.recompute(); doc.saveAs(str(ROOT/'column-reuse-study.FCStd'))
    m.Part.export(doc.Objects, str(ROOT/'column-reuse-study.step'))
    report['cad_objects'] = len(doc.Objects)
    report['brep_solids_valid'] = True
    report['assembly'] = 'Stack columns and bearing-tab arms; fit track as segments. Track segmentation not yet designed.'
    report['status'] = 'Concept assembly; physical fit, rigidity and loading not tested.'
    m.App.closeDocument(doc.Name)
    (ROOT/'column-reuse-checks.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    export_and_check()
    exploded(); print('17 rendered', flush=True)
    layout(); print('18 rendered', flush=True)
    sections(); print('19 rendered', flush=True)
