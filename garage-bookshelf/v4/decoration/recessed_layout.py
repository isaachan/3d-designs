"""Approved four-floor parking layout, in deck-local front-left coordinates.

The accessible bay is twice the normal bay width. Tray interfaces stay uniform.
These vectors are shared by native CAD engravings and preview tooling.
"""
from .generate import design, lettering, wheelchair, W, D, WHITE, YELLOW, ACCESS_BLUE

REFERENCE_WIDTH=195.6
FLOORS={'module_1':(1,2),'garage_deck_1':(2,2),
        'garage_deck_2':(3,3),'garage_deck_3':(4,3)}


def bay_edges(count,width):
    sx=width/W;left=27.8*sx;unit=48*sx
    return [left,left+2*unit,left+3*unit] if count==2 else [left+i*unit for i in range(4)]


def center_ratio(count,index):
    edges=bay_edges(count,W)
    return (edges[index]+edges[index+1])/2/W


def points(item):
    if item['kind']=='rect':
        x,y,w,h=[item[k] for k in ('x','y','w','h')]
        return [(x,y),(x+w,y),(x+w,y+h),(x,y+h)]
    return item['points']


def polygons(count,floor,width=REFERENCE_WIDTH,depth=D):
    sx,sy=width/W,depth/D
    result=[];edges=bay_edges(count,width)
    centers=[(a+b)/2 for a,b in zip(edges,edges[1:])]
    old_cx=27.8+72/2
    for item in design(count):
        xy=points(item);xs,ys=zip(*xy)
        if item['color']==ACCESS_BLUE:continue
        if item['color']==WHITE:
            if min(ys)>118.18 and max(ys)<122.23:continue
            if count==2 and min(xs)>old_cx-15 and max(xs)<old_cx+17 and min(ys)>50 and max(ys)<100:continue
            if count==2 and item['kind']=='rect' and abs(item['y']-25.2)<1e-6 and abs(item['h']-90.6)<1e-6:continue
        if count==2 and item['color']==YELLOW and item['kind']=='rect' and abs(item['y']-28.8)<1e-6 and abs(item['h']-2)<1e-6:continue
        result.append((item['color'],[(x*sx,depth-y*sy) for x,y in xy]))
    if count==2:
        for x in edges:
            result.append((WHITE,[(x-.6*sx,42.8*sy),(x+.6*sx,42.8*sy),
                                  (x+.6*sx,133.4*sy),(x-.6*sx,133.4*sy)]))
        for cx in centers:
            result.append((YELLOW,[(cx-10*sx,127.8*sy),(cx+10*sx,127.8*sy),
                                   (cx+10*sx,129.8*sy),(cx-10*sx,129.8*sy)]))
    ids=[]
    for i,cx in enumerate(centers,1):
        lettering(ids,f'{floor}0{i}',cx/sx,120.2,4,WHITE)
    for item in ids:
        result.append((item['color'],[(x*sx,depth-y*sy) for x,y in points(item)]))
    if count==2:
        bay_left,bay_right=edges[:2];cx=centers[0]
        slot_left,slot_right=cx-20.3,cx+20.3
        for x0,x1 in [(bay_left+.6*sx,slot_left-1),(slot_right+1,bay_right-.6*sx)]:
            result.append((ACCESS_BLUE,[(x0,47.2*sy),(x1,47.2*sy),(x1,125.8*sy),(x0,125.8*sy)]))
        result.append((ACCESS_BLUE,[(cx-9,11*sy),(cx+9,11*sy),(cx+9,29*sy),(cx-9,29*sy)]))
        symbol=[];wheelchair(symbol,0,0)
        for item in symbol:
            result.append((WHITE,[(cx+x*.46,(20-y*.46)*sy) for x,y in points(item)]))
    return result
