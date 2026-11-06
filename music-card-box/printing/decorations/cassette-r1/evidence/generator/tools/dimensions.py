"""Draw a dimension/installation sheet using the frozen design input."""
import argparse
import json
from pathlib import Path
import math
from PIL import Image,ImageDraw,ImageFont
import _bootstrap
from _bootstrap import ROOT

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    if not args.output.resolve().is_relative_to(ROOT/'build') or args.output.exists():
        parser.error('Use a new file under build/.')
    spec=json.loads((ROOT/'assets/design.json').read_text());p=spec['dimensions_mm']
    im=Image.new('RGB',(2200,1450),'#F5F5EF');d=ImageDraw.Draw(im)
    font_path='/System/Library/Fonts/STHeiti Medium.ttc'
    def font(size):return ImageFont.truetype(font_path,size)
    navy=spec['colors']['darkblue'];blue=spec['colors']['lightblue'];yellow=spec['colors']['yellow'];ink='#26394C';muted='#657786'
    def label(x,y,text,size=30,fill=ink,anchor=None):d.text((x,y),text,font=font(size),fill=fill,anchor=anchor)
    def arrow(a,b,text,vertical=False,offset=0):
        d.line([a,b],fill=muted,width=2)
        dx=b[0]-a[0];dy=b[1]-a[1];length=math.hypot(dx,dy);ux=dx/length;uy=dy/length
        for pt,sgn in [(a,1),(b,-1)]:
            q=(pt[0]+sgn*ux*12,pt[1]+sgn*uy*12)
            d.polygon([pt,(q[0]-uy*5,q[1]+ux*5),(q[0]+uy*5,q[1]-ux*5)],fill=muted)
        cx=(a[0]+b[0])/2;cy=(a[1]+b[1])/2
        label(cx+(18 if vertical else 0),cy+(offset if vertical else -26),text,27,anchor='lm' if vertical else 'mm')
    label(80,52,'笑脸磁带卡片盒',60,navy)
    label(82,132,'r1   /   单位 mm   /   正交尺寸示意，非 1:1 打印模板',27,muted)
    for box in [(70,210,1110,910),(1150,210,2130,910),(70,960,745,1370),(775,960,1450,1370),(1480,960,2130,1370)]:
        d.rounded_rectangle(box,24,fill='white')
    label(105,238,'正面 · 卡片横放',32)
    cx=565;base=770;s=4.25
    X=lambda x:cx+x*s
    Z=lambda z:base-z*s
    w=p['InnerWidth']+2*p['Wall']
    d.rounded_rectangle([X(-w/2),Z(92),X(w/2),base],radius=22,fill=navy)
    d.rounded_rectangle([X(-90),Z(104.2),X(90),Z(3.2)],radius=6,fill='#EFF4EF',outline='#B9C9D4',width=3)
    label(X(-78),Z(99),'♪  Sing a little song',20,navy)
    for z in [85,87,89,91]:d.line((X(-78),Z(z),X(78),Z(z)),fill='#A6B8C7',width=1)
    pts=[(X(-w/2),base),(X(w/2),base),(X(w/2),Z(76)),(X(35),Z(76)),(X(35),Z(70))]
    pts += [(X(25+10*math.cos(a)),Z(70+10*math.sin(a))) for a in [-(math.pi/2)*i/16 for i in range(17)]]
    pts += [(X(-25),Z(60))]
    pts += [(X(-25+10*math.cos(a)),Z(70+10*math.sin(a))) for a in [-math.pi/2-math.pi/2*i/16 for i in range(17)]]
    pts += [(X(-35),Z(76)),(X(-w/2),Z(76))]
    d.polygon(pts,fill=navy)
    d.rounded_rectangle([X(-86),Z(58),X(86),Z(14)],radius=20,fill=blue)
    for x in [-47,47]:
        d.ellipse([X(x-14),Z(51),X(x+14),Z(23)],fill='#F6F7F2')
        d.ellipse([X(x-5.8),Z(42.8),X(x+5.8),Z(31.2)],fill=navy)
    label(cx,Z(43),'♫',72,yellow,'mm')
    d.arc([X(-11),Z(27),X(11),Z(18)],0,180,fill=navy,width=8)
    d.polygon([(X(-33),Z(4.5)),(X(33),Z(4.5)),(X(28),Z(11.5)),(X(-28),Z(11.5))],fill='#F6F7F2')
    arrow((X(-w/2),825),(X(w/2),825),'190.4')
    arrow((X(-90),300),(X(90),300),'卡片 180')
    arrow((1010,Z(3.2)),(1010,Z(104.2)),'101',True)
    label(115,865,'前沿 76 / 中央 60；卡片顶端距盒底 104.2',25,muted)
    label(1185,238,'侧面 · 留出手指空间',32)
    y0=1320;ss=5.2
    Y=lambda y:y0+y*ss
    ZZ=lambda z:base-z*4.25
    d.rectangle((Y(-2),ZZ(110),Y(0),base+5),fill='#D4D9DD')
    d.rectangle((Y(0),ZZ(92),Y(3.2),base),fill=navy)
    d.rectangle((Y(3.2),ZZ(70),Y(10.2),ZZ(3.2)),fill='#547BA8')
    d.rectangle((Y(0),ZZ(3.2),Y(38.4),base),fill=navy)
    d.rectangle((Y(35.2),ZZ(76),Y(38.4),base),fill=navy)
    d.rectangle((Y(12.7),ZZ(104.2),Y(32.7),ZZ(3.2)),fill='#EFF4EF',outline='#B9C9D4',width=3)
    d.rectangle((Y(38.6),ZZ(58),Y(40.4),ZZ(14)),fill=blue)
    arrow((Y(0),825),(Y(38.4),825),'38.4')
    label(1600,370,'后侧垫筋 7',27)
    d.line((1580,400,Y(7),ZZ(65)),fill=muted,width=2)
    label(1600,455,'卡片离墙 ≥ 10.2',27)
    d.line((1580,485,Y(11),ZZ(98)),fill=muted,width=2)
    label(1600,550,'有效净厚 25',27)
    label(1600,598,'容纳约 20 厚整摞',24,muted)
    label(1600,680,'含装饰最大深度 42.2',24,muted)
    label(1190,865,'上方至少留 115，向上抽卡；胶厚另计',25,muted)
    label(105,995,'顺手取放',32,navy)
    label(110,1065,'正面中央露出 44.2',29)
    label(110,1120,'背面中央露出 28.2',29)
    label(110,1193,'顶部敞开，斜侧口引导放入',25,muted)
    label(110,1245,'后侧留空，手指可从背面夹取',25,muted)
    label(110,1305,'宽度总余量 4 / 厚度总余量 5',24,muted)
    label(810,995,'背面贴胶区域',32,navy)
    rx=880;rz=1300;rs=2.25
    d.rounded_rectangle((rx,rz-92*rs,rx+w*rs,rz),10,fill=navy)
    for x,z,width,height in spec['adhesive_zones_mm']:
        d.rounded_rectangle((rx+(x+w/2)*rs,rz-(z+height)*rs,rx+(x+w/2+width)*rs,rz-z*rs),4,fill=yellow)
    label(815,1320,'4 处 20 × 60；平面无凹槽',24,muted)
    label(1515,995,'打印与验证',32,navy)
    label(1520,1065,'主体直立打印，开口朝上',29)
    label(1520,1130,'装饰分色平放，打印后粘贴',27)
    label(1520,1200,'CAD / 网格检查已通过',26)
    label(1520,1255,'切片、取放与胶粘承载待实测',24,muted)
    label(80,1400,'卡片包络 180 × 101 × 20   |   深蓝 · 浅蓝 · 白色 · 黄色',25,muted)
    im.save(args.output)
    print(args.output)

if __name__=='__main__':main()
