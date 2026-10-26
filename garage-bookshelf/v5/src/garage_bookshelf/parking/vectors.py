"""Parking graphics in mm. No CAD/STL or slicer projects are modified.

Run with the Codex bundled Python (Pillow and ReportLab required).
SVG and PDF use the same vector primitives. Origin: rear-left, +y toward front.
"""
from pathlib import Path
import json
import math


# Vector primitives only; output generation is archived.
W, D = 199.6, 158.6
HOLES = [(13.8, 13.8), (185.8, 13.8), (13.8, 144.8), (185.8, 144.8)]
WHITE, YELLOW, DECK = '#f7f6ec', '#f3c945', '#62686b'
BAY_DEPTH = 90
ACCESS_BLUE = '#236aaf'
FONT = {
    '0': ['111', '101', '101', '101', '111'],
    '1': ['010', '110', '010', '010', '111'],
    '2': ['111', '001', '111', '100', '111'],
    '3': ['111', '001', '111', '001', '111'],
    '4': ['101', '101', '111', '001', '001'],
    'A': ['010', '101', '111', '101', '101'],
    'B': ['110', '101', '110', '101', '110'],
    'P': ['110', '101', '110', '100', '100'],
}


def rect(out, x, y, w, h, color):
    out.append(dict(kind='rect', x=x, y=y, w=w, h=h, color=color))


def polygon(out, points, color):
    out.append(dict(kind='polygon', points=points, color=color))


def bay_width(count):
    return 144 / count


def bay_boundaries(count):
    # Restore the original full-width layouts: three 48 mm or two 72 mm bays.
    return [27.8 + i*bay_width(count) for i in range(count+1)]


def disk(out, x, y, r, color):
    polygon(out, [(x+r*math.cos(i*math.tau/48),
                   y+r*math.sin(i*math.tau/48)) for i in range(48)], color)


def thick_segment(out, a, b, thickness, color):
    dx,dy=b[0]-a[0],b[1]-a[1]
    length=math.hypot(dx,dy)
    nx,ny=-dy/length*thickness/2,dx/length*thickness/2
    polygon(out,[(a[0]+nx,a[1]+ny),(b[0]+nx,b[1]+ny),
                 (b[0]-nx,b[1]-ny),(a[0]-nx,a[1]-ny)],color)
    disk(out,*a,thickness/2,color)
    disk(out,*b,thickness/2,color)


def wheelchair(out,cx,cy):
    # Vector-only wheelchair pictogram, independent of fonts and PDF encoding.
    disk(out,cx-1,cy-12,2.6,WHITE)
    center=(cx-5,cy+6)
    angles=[math.radians(20+i*320/64) for i in range(65)]
    polygon(out,[(center[0]+8*math.cos(a),center[1]+8*math.sin(a)) for a in angles]
            +[(center[0]+6*math.cos(a),center[1]+6*math.sin(a)) for a in reversed(angles)],WHITE)
    points=[(cx-2,cy-7),(cx-4,cy+1),(cx+5,cy+1),(cx+9,cy+10),(cx+14,cy+8)]
    for a,b in zip(points,points[1:]): thick_segment(out,a,b,2.2,WHITE)


def lettering(out, text, cx, y, height, color):
    # Embedded stencil-like pixel glyphs keep physical text dimensions portable.
    p = height / 5
    width = (len(text) * 4 - 1) * p
    x = cx - width / 2
    for k, letter in enumerate(text):
        for row, bits in enumerate(FONT[letter]):
            for col, bit in enumerate(bits):
                if bit == '1':
                    # A 0.02 mm shared overlap prevents corner-only contacts in
                    # B/0/P glyphs when the same vectors become native CAD cuts.
                    rect(out, x + (4*k + col)*p-.01, y + row*p-.01, p+.02, p+.02, color)


def design(count):
    out = []
    xs = bay_boundaries(count)
    if count==2:
        # B01 retains the original 72 x 90 mm footprint with a wheelchair mark.
        rect(out,xs[0]+.6,26.4,bay_width(count)-1.2,BAY_DEPTH-.6,ACCESS_BLUE)
        wheelchair(out,(xs[0]+xs[1])/2,72)
    # Rear line and sides only: open toward the front circulation lane.
    rect(out, 27.2, 25.2, 145.2, 1.2, WHITE)
    for x in xs:
        rect(out, x-.6, 25.2, 1.2, 90.6, WHITE)
    for i in range(count):
        cx = (xs[i]+xs[i+1])/2
        lettering(out, ('A' if count == 3 else 'B') + '0' + str(i+1), cx, 118.2, 4, WHITE)
        # Flat painted wheel-stop motif, no raised obstacle.
        rect(out, cx-10, 28.8, 20, 2.0, YELLOW)
    # Side no-parking bands, kept between front and rear supports.
    for x0 in [4.5, 177.5]:
        rect(out, x0, 29.8, 17.6, 1, YELLOW)
        rect(out, x0, 107.8, 17.6, 1, YELLOW)
        rect(out, x0, 29.8, 1, 79, YELLOW)
        rect(out, x0+16.6, 29.8, 1, 79, YELLOW)
        for y in range(34, 98, 8):
            polygon(out, [(x0+1, y+8), (x0+1, y+10), (x0+16.6, y+1.5), (x0+16.6, y-.5)], YELLOW)
    # Pedestrian crossing over the aisle, walking toward the parking bays.
    for i in range(6):
        rect(out, 30.5, 125.8 + i*4.5, 23, 2.5, WHITE)
    # Directional arrow pointing right along the aisle.
    polygon(out, [(89,137.2),(119,137.2),(119,132.8),(130,139.8),
                  (119,146.8),(119,142.4),(89,142.4)], WHITE)
    # Discrete front edge dashes, clear of the crossing and the columns.
    for x in [64, 76, 88, 100, 112, 124, 136, 148, 160]:
        rect(out, x, 153.3, 6, .8, YELLOW)
    # Parking pictogram in the free portion of the front aisle.
    lettering(out, 'P', 155, 132.5, 11, WHITE)
    return out
