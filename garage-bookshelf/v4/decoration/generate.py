"""Parking graphics in mm. No CAD/STL or slicer projects are modified.

Run with the Codex bundled Python (Pillow and ReportLab required).
SVG and PDF use the same vector primitives. Origin: rear-left, +y toward front.
"""
from pathlib import Path
import json
import math


ROOT = Path(__file__).resolve().parent
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


def svg(count, graphics_only=False):
    items = design(count)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{D}mm" viewBox="0 0 {W} {D}">',
           f'<title>{count}-bay parking markings, {W} x {D} mm</title>',
           '<desc>Rear at top; front at bottom. Four holes diameter 6.5 mm. Transparent SVG contains only paint graphics.</desc>']
    if not graphics_only:
        out.append(f'<rect width="{W}" height="{D}" fill="{DECK}"/>')
    out.append('<g id="paint-markings">')
    for a in items:
        if a['kind']=='rect':
            out.append(f'<rect x="{a["x"]:.4f}" y="{a["y"]:.4f}" width="{a["w"]:.4f}" height="{a["h"]:.4f}" fill="{a["color"]}"/>')
        else:
            pts = ' '.join(f'{x:.4f},{y:.4f}' for x,y in a['points'])
            out.append(f'<polygon points="{pts}" fill="{a["color"]}"/>')
    out.append('</g>')
    if not graphics_only:
        out.append('<g id="hole-and-column-reference">')
        for x,y in HOLES:
            out.append(f'<circle cx="{x}" cy="{y}" r="11" fill="none" stroke="#b5bdbe" stroke-width=".3" stroke-dasharray="1.2 1.2"/>')
            out.append(f'<circle cx="{x}" cy="{y}" r="3.25" fill="#eef0ed"/>')
        out.append('</g>')
    return '\n'.join(out+['</svg>'])


def draw_pdf_plate(c, count, low_ink):
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor
    c.saveState()
    c.translate(18*mm, (24+D)*mm)
    c.scale(mm, -mm)
    if not low_ink:
        c.setFillColor(HexColor(DECK))
        c.rect(0,0,W,D,fill=1,stroke=0)
    for a in design(count):
        if low_ink and a['color']==ACCESS_BLUE:
            continue  # Keep the black wheelchair visible on white paper.
        color = '#25292b' if low_ink else a['color']
        c.setFillColor(HexColor(color))
        if a['kind']=='rect':
            c.rect(a['x'],a['y'],a['w'],a['h'],fill=1,stroke=0)
        else:
            p=c.beginPath()
            p.moveTo(*a['points'][0])
            for xy in a['points'][1:]: p.lineTo(*xy)
            p.close()
            c.drawPath(p,fill=1,stroke=0)
    c.setLineWidth(.25)
    c.setStrokeColor(HexColor('#444444' if low_ink else '#ccd0d1'))
    c.rect(0,0,W,D,stroke=1,fill=0)
    for x,y in HOLES:
        c.setDash(1,1)
        c.circle(x,y,11,stroke=1,fill=0)
        c.setDash()
        c.setFillColor(HexColor('#ffffff'))
        c.circle(x,y,3.25,stroke=1,fill=1)
    c.restoreState()


def make_pdf():
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.colors import HexColor
    dest=ROOT/'output/pdf/parking-layouts-actual-size.pdf'
    dest.parent.mkdir(parents=True,exist_ok=True)
    c=canvas.Canvas(str(dest), pagesize=landscape(A4))
    c.setTitle('Garage bookshelf v4 - parking deck markings, actual size')
    for low_ink in [False,True]:
        for count in [3,2]:
            c.setFillColor(HexColor('#20282b'))
            c.setFont('Helvetica-Bold',13)
            c.drawString(18*mm,197*mm,f'{count} BAYS / '+('PAPER FIT CHECK' if low_ink else 'COLOR PROOF'))
            c.setFont('Helvetica',8)
            c.drawString(18*mm,190*mm,'GARAGE BOOKSHELF v4   /   REAR AT TOP - FRONT AT BOTTOM')
            draw_pdf_plate(c,count,low_ink)
            lines=[('ACTUAL SIZE',11),('199.6 x 158.6 mm',9),('',8),
                   (f'Bay: {bay_width(count):.0f} x {BAY_DEPTH} mm',9),('Line width: 1.2 mm',9),
                   ('4 holes: diameter 6.5 mm',9),('Dotted radius: 11 mm',9),
                   ('Dotted circles = reference',8),('for column keep-out only.',8),('',8),
                   ('Print A4 landscape',9),('Scale 100% / Actual size',9),
                   ('Disable fit-to-page.',9),('',8),('Cut at the outer rectangle.',8),
                   ('Test with your actual cars.',8)]
            if count==2:
                lines += [('',8),('B01: wheelchair marking',8)]
            y=179
            for text,size in lines:
                c.setFont('Helvetica-Bold' if text=='ACTUAL SIZE' else 'Helvetica',size)
                c.drawString(229*mm,y*mm,text); y-=5.2
            c.setFont('Helvetica',8)
            c.drawString(229*mm,44*mm,'50 mm calibration')
            c.setLineWidth(.7)
            c.line(229*mm,38*mm,279*mm,38*mm)
            for x in [229,279]: c.line(x*mm,36*mm,x*mm,40*mm)
            c.setFont('Helvetica',7)
            c.drawString(18*mm,15*mm,'Vector layout for 0.2/0.4 mm pocket engraving. Wheel-stop motifs are flat paint-fill markings.')
            c.showPage()
    c.save()


def preview_plate(count, occupied):
    from PIL import Image, ImageDraw
    s=5
    im=Image.new('RGB',(round(W*s),round(D*s)),DECK)
    d=ImageDraw.Draw(im)
    for a in design(count):
        if a['kind']=='rect':
            d.rectangle((a['x']*s,a['y']*s,(a['x']+a['w'])*s,(a['y']+a['h'])*s),fill=a['color'])
        else: d.polygon([(x*s,y*s) for x,y in a['points']],fill=a['color'])
    for x,y in HOLES:
        d.ellipse(((x-11)*s,(y-11)*s,(x+11)*s,(y+11)*s),outline='#b6bdbf',width=2)
        # Actual column shaft, represented in preview only.
        d.ellipse(((x-7)*s,(y-7)*s,(x+7)*s,(y+7)*s),fill=YELLOW,outline='#ffe58b',width=3)
    if occupied:
        xs=bay_boundaries(count)
        for i in range(count):
            cx=(xs[i]+xs[i+1])/2
            # 85 x 38 mm is a fit-check envelope, not a measurement of the photos.
            x0,x1=(cx-19)*s,(cx+19)*s
            y0,y1=28.3*s,113.3*s
            color=['#b73d38','#262b30','#e0e4df'][i]
            d.rounded_rectangle((x0,y0,x1,y1),radius=9*s,fill=color,outline='#bcc5c5',width=2)
            d.rounded_rectangle(((cx-14)*s,51*s,(cx+14)*s,86*s),radius=4*s,fill='#121d25',outline='#8e9b9d',width=2)
            d.line(((cx-14)*s,63*s,(cx+14)*s,63*s),fill='#8e9b9d',width=2)
            d.line(((cx-14)*s,77*s,(cx+14)*s,77*s),fill='#8e9b9d',width=2)
            d.rounded_rectangle(((cx-14)*s,104*s,(cx-7)*s,106*s),radius=s,fill='#f6ecd2')
            d.rounded_rectangle(((cx+7)*s,104*s,(cx+14)*s,106*s),radius=s,fill='#f6ecd2')
    return im


def make_preview():
    from PIL import Image, ImageDraw, ImageFont
    canvas_im=Image.new('RGB',(2200,2060),'#eeede7')
    d=ImageDraw.Draw(canvas_im)
    face='/System/Library/Fonts/Helvetica.ttc'
    title=ImageFont.truetype(face,52)
    label=ImageFont.truetype(face,32)
    small=ImageFont.truetype(face,25)
    d.text((70,38),'GARAGE / PARKING GRAPHICS',font=title,fill='#273136')
    d.text((70,106),'v4  /  199.6 x 158.6 mm  /  rear at top, front at bottom',font=small,fill='#60696b')
    for col,count in enumerate([3,2]):
        x=70+col*1060
        d.text((x,170),f'{count} BAYS   /   {bay_width(count):.0f} x {BAY_DEPTH} mm per bay',font=label,fill='#273136')
        canvas_im.paste(preview_plate(count,False),(x,230))
        d.text((x,1060),'FIT STUDY  /  85 x 38 mm illustrative vehicles',font=small,fill='#60696b')
        canvas_im.paste(preview_plate(count,True),(x,1110))
    d.text((70,1960),'Yellow discs: existing columns. Rings: 11 mm keep-out. Flat paint graphics only.',font=small,fill='#60696b')
    canvas_im.save(ROOT/'parking-layout-comparison.png')


def validate():
    # Real geometric check: painted polygons avoid all four 11 mm keep-outs.
    def segment_distance(p,a,b):
        dx,dy=b[0]-a[0],b[1]-a[1]
        t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(dx*dx+dy*dy)))
        return math.dist(p,(a[0]+t*dx,a[1]+t*dy))
    results=[]
    for count in [3,2]:
        xs=bay_boundaries(count)
        assert all(math.isclose(b-a,bay_width(count)) for a,b in zip(xs,xs[1:]))
        minimum=1e9
        for a in design(count):
            if a['kind']=='rect':
                x,y,w,h=[a[k] for k in ['x','y','w','h']]
                poly=[(x,y),(x+w,y),(x+w,y+h),(x,y+h)]
            else: poly=a['points']
            assert all(0<=x<=W and 0<=y<=D for x,y in poly)
            for center in HOLES:
                dist=min(segment_distance(center,poly[i-1],p) for i,p in enumerate(poly))
                assert dist>=11, (count,center,dist)
                minimum=min(minimum,dist)
        results.append(dict(bays=count,bay_width_mm=bay_width(count),bay_depth_mm=BAY_DEPTH,
                            bay_x_boundaries_mm=xs,
                            accessible_bay='B01' if count==2 else None,
                            side_access_zone_x_range_mm=None,
                            minimum_paint_distance_from_hole_center_mm=round(minimum,3),
                            clear_of_11mm_keepouts=True,vehicle_example_mm=[85,38],
                            bay_side_clearance_for_example_vehicle_mm=(bay_width(count)-38)/2))
    (ROOT/'layout-specification.json').write_text(json.dumps(dict(
        board_mm=[W,D,5],coordinate_system='rear-left origin, +x right, +y toward front',
        hole_centers_mm=HOLES,hole_diameter_mm=6.5,column_shaft_radius_mm=7,
        paint_keepout_radius_mm=11,bay_x_range_mm=[27.8,171.8],bay_y_range_mm=[25.8,115.8],
        front_aisle_nominal_depth_mm=42.8,line_width_mm=1.2,
        car_sizes_are_illustrative_not_photo_measurements=True,layouts=results
    ),indent=2)+'\n')


def main():
    validate()
    for count in [3,2]:
        (ROOT/f'parking-{count}-bays-proof.svg').write_text(svg(count))
        (ROOT/f'parking-{count}-bays-markings.svg').write_text(svg(count,True))
    make_pdf()
    make_preview()
    print('Validated both layouts; wrote 4 SVGs, comparison PNG, 4-page actual-size PDF and JSON specification.')


if __name__=='__main__': main()
