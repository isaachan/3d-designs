"""Freeze the chosen local font outline; normal CAD rebuilds need no font/matplotlib.

Adaptive Bezier flattening is bounded to 0.015 mm at the largest 16 mm line.
This stores only the requested lettering outlines, not a copy of the font file.
"""
import hashlib,json
from pathlib import Path
import numpy as np
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
from matplotlib.path import Path as MPath
ROOT=Path(__file__).resolve().parent
FONT=Path('/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf')
LINES=[('NO HORSEPOWER.',16),('ONLY BRAINPOWER.',16)]


def flatten(points,tolerance):
    a=points[0];b=points[-1];chord=b-a;length=np.linalg.norm(chord)
    distance=max((abs(np.cross(chord,p-a))/length if length else np.linalg.norm(p-a)) for p in points[1:-1])
    if distance<=tolerance:return [b]
    levels=[points]
    while len(levels[-1])>1:levels.append((levels[-1][:-1]+levels[-1][1:])/2)
    left=np.array([level[0] for level in levels]);right=np.array([level[-1] for level in reversed(levels)])
    return flatten(left,tolerance)+flatten(right,tolerance)


def main():
    font=FontProperties(fname=str(FONT));rows=[]
    for text,height in LINES:
        path=TextPath((0,0),text,size=10,prop=font);bb=path.get_extents()
        polygons=[];current=[];last=None
        for values,code in path.iter_segments(curves=True,simplify=False):
            points=np.asarray(values).reshape(-1,2)
            if code==MPath.MOVETO:current=[points[0]];last=points[0]
            elif code==MPath.LINETO:current.append(points[0]);last=points[0]
            elif code in (MPath.CURVE3,MPath.CURVE4):
                current.extend(flatten(np.vstack([last,points]),.015*bb.height/16));last=points[-1]
            elif code==MPath.CLOSEPOLY:
                if np.linalg.norm(current[-1]-current[0])<1e-8:current.pop()
                normalized=[[(float(x)-bb.xmin)/bb.height,(float(y)-bb.ymin)/bb.height] for x,y in current]
                polygons.append(normalized)
        assert polygons
        # Group each outer contour with its holes to keep native sketch solvers small.
        areas=[abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(poly,poly[1:]+poly[:1]))/2) for poly in polygons]
        parents=[]
        for i,poly in enumerate(polygons):
            enclosing=[j for j,other in enumerate(polygons) if j!=i and MPath(np.array(other+[other[0]])).contains_point(poly[0])]
            parents.append(min(enclosing,key=lambda j:areas[j]) if enclosing else None)
        glyphs=[[i]+[j for j,parent in enumerate(parents) if parent==i] for i,parent in enumerate(parents) if parent is None]
        assert sum(map(len,glyphs))==len(polygons)
        rows.append(dict(glyphs=glyphs,text=text,cap_height_mm=height,
                         width_per_cap_height=bb.width/bb.height,polygons=polygons))
    output=dict(slogan='NO HORSEPOWER. ONLY BRAINPOWER.',rotation_degrees=-90,reading_direction='top_to_bottom',font='DIN Condensed Bold',
                source_font_sha256=hashlib.sha256(FONT.read_bytes()).hexdigest(),
                maximum_outline_deviation_mm=.015,lines=rows)
    (ROOT/'sign-lettering.json').write_text(json.dumps(output,ensure_ascii=False,indent=2))
    print([(r['text'],r['cap_height_mm']*r['width_per_cap_height'],sum(map(len,r['polygons']))) for r in rows])

if __name__=='__main__':main()
