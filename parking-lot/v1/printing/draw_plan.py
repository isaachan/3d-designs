"""Write a vector assembly locator; all dimensions and angles are in mm."""
import math
from pathlib import Path
import xml.etree.ElementTree as E

ROOT = Path(__file__).resolve().parent
SVG = 'http://www.w3.org/2000/svg'
E.register_namespace('', SVG)


def main():
    root = E.Element('{'+SVG+'}svg', width='1100', height='720', viewBox='0 0 1100 720')
    def add(tag, **attrs):
        return E.SubElement(root, '{'+SVG+'}'+tag, {k.replace('_','-'):str(v) for k,v in attrs.items()})
    def xy(x,y):
        return 35+(x+10)*1.05, 530-(y+108.357)*1.05
    def text(x,y,value,size=16,fill='#20323d',anchor='start'):
        o = add('text', x=x, y=y, fill=fill, font_size=size, text_anchor=anchor,
                font_family='Hiragino Sans GB, sans-serif')
        o.text = value
    def line(x0,y0,x1,y1,**style):
        x0,y0 = xy(x0,y0)
        x1,y1 = xy(x1,y1)
        add('line', x1=x0,y1=y0,x2=x1,y2=y1,**style)
    def rectangle(x0,y0,x1,y1,**style):
        x,y = xy(x0,y1)
        add('rect', x=x,y=y,width=(x1-x0)*1.05,height=(y1-y0)*1.05,**style)
    def sector(a,b,fill):
        points = []
        for radius, angles in [(155, [a+(b-a)*j/50 for j in range(51)]),
                               (85, [b+(a-b)*j/50 for j in range(51)])]:
            points += [xy(410+radius*math.cos(t),75+radius*math.sin(t)) for t in angles]
        add('polygon', points=' '.join(f'{x:.2f},{y:.2f}' for x,y in points), fill=fill, stroke='#61788a', stroke_width='1')
    add('rect', width=1100, height=720, fill='#f7f9fb')
    text(35,48,'Parking Lot v1 · 打印件装配定位',30)
    text(35,83,'俯视示意 · 单位 mm · 四层道路投影重合；图中灰度仅用于区分拆件',18,'#536674')
    rectangle(-10,-92,625,242,fill='#e1e7ec',stroke='#8296a5',stroke_width=2)
    for degree in (35,95,275):
        t = math.radians(degree)
        x,y = xy(410+169*math.cos(t),75+169*math.sin(t))
        add('circle',cx=x,cy=y,r=15*1.05,fill='#d5dde4',stroke='#8296a5')
    x,y = xy(602,74)
    add('circle',cx=x,cy=y,r=15*1.05,fill='#d5dde4',stroke='#8296a5')
    rectangle(0,0,200,230,fill='#c8d4df',stroke='#61788a',stroke_width=2)
    for x in (200,410):
        line(x,-92,x,242,stroke='#f05d3d',stroke_width=2,stroke_dasharray='7 5')
    line(-10,110,625,110,stroke='#f05d3d',stroke_width=2,stroke_dasharray='7 5')
    for label,x,y in [('01 / 底座1·1',95,-125),('02 / 底座1·2',95,280),('03 / 底座2·1',305,-125),
                       ('04 / 底座2·2',305,280),('05 / 底座3·1',535,-125),('06 / 底座3·2',535,280)]:
        xx,yy = xy(x,y)
        text(xx,yy,label,14,'#415d70','middle')
    a,b = math.radians(205),math.radians(515)
    cuts = [a+(b-a)*i/4 for i in range(5)]
    sector(math.radians(155),math.radians(205),'#efd69d')
    rectangle(200,40,255,110,fill='#efd69d',stroke='#61788a')
    for i,(lo,hi) in enumerate(zip(cuts,cuts[1:]),1):
        sector(lo,hi,'#bdd1df' if i%2 else '#d4e1eb')
        mid=(lo+hi)/2
        xx,yy=xy(410+120*math.cos(mid),75+120*math.sin(mid))
        text(xx,yy+7,f'R{i}',22,'#203b50','middle')
    for theta in cuts:
        for radius in (105,135):
            x,y=xy(410+radius*math.cos(theta),75+radius*math.sin(theta))
            add('circle',cx=x,cy=y,r=3.7,fill='#e65332')
    for x in (60,140):
        xx,yy=xy(x,110)
        add('circle',cx=xx,cy=yy,r=3.7,fill='#e65332')
    for label,degree in [('B1',35),('B2',95),('B3',275)]:
        theta=math.radians(degree)
        x,y=xy(410+169*math.cos(theta),75+169*math.sin(theta))
        text(x,y+6,label,17,'#20323d','middle')
    x,y=xy(602,74)
    text(x,y+6,'C',17,'#20323d','middle')
    x,y=xy(225,75)
    text(x,y+5,'L1–L4',14,'#674600','middle')
    text(760,170,'拆件对应',24)
    for i,value in enumerate(['R1–R4：每圈的四个升坡片',
                              '第一圈 13–16 盘：浅蓝',
                              '第二圈 17–20 盘：深蓝',
                              '第三圈 21–24 盘：红色',
                              'L1–L4：25–28 号盘',
                              '07–12：二至四楼的平台半片',
                              '29：29 个原柱段／封顶段',
                              '30：托臂、定高底段与侧牌框',
                              '31：定位销、圆垫、连接片',
                              '32：背板；33：标牌与标签']):
        text(760,210+i*30,value,16,'#415d70')
    text(35,590,'红色虚线：底座／层板拼缝；红点：每处两根 Ø3 × 10 定位销，孔 Ø3.3、单侧深 5.2。',18)
    text(35,626,'底座 X 分界 200、410；Y 分界 110。道路及层板拼缝先干装，再胶粘；底座拼缝另加底侧连接片。',17,'#536674')
    text(35,660,'L1–L4 采用公共轮廓示意；4F 前缘按最终 CAD／3MF 齐边收口。请结合装配说明查看叠装次序。',17,'#536674')
    (ROOT/'assembly-plan.svg').write_bytes(E.tostring(root,encoding='utf-8',xml_declaration=True))


if __name__=='__main__':
    main()
