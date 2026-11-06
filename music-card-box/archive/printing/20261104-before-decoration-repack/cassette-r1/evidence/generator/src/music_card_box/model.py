"""Six editable native solids, designed in wall coordinates: +Y away from wall."""
import json
from pathlib import Path
import FreeCAD as App
from .native import rectangle, polygon, circles, feature, fillet, edges_along_y

def build(spec):
    doc = App.newDocument('MusicCardBox')
    params = doc.addObject('Spreadsheet::Sheet','Parameters')
    params.Label = 'Dimensions in mm · r1'
    for row,(name,number) in enumerate(spec['dimensions_mm'].items(),1):
        params.set('A'+str(row),name)
        params.set('B'+str(row),str(number)+' mm')
        params.setAlias('B'+str(row),name)
    row=len(spec['dimensions_mm'])+1
    for name,expression in [('OuterWidth','InnerWidth+2*Wall'),('OuterDepth','InnerDepth+2*Wall')]:
        params.set('A'+str(row),name)
        params.set('B'+str(row),'='+expression)
        params.setAlias('B'+str(row),name)
        row+=1
    doc.recompute()
    p=spec['dimensions_mm']; w=p['InnerWidth']+2*p['Wall']; depth=p['InnerDepth']+2*p['Wall']
    parts={}
    def body(name):
        b=doc.addObject('PartDesign::Body',name)
        b.addProperty('App::PropertyString','PrintColor','Manufacturing')
        b.PrintColor=spec['print_parts'][name]
        b.addProperty('App::PropertyString','Revision','Manufacturing'); b.Revision=spec['revision']
        parts[name]=b
        return b
    b=body('CassetteShell')
    s=rectangle(b,'ShellEnvelope','-OuterWidth/2','0 mm','OuterWidth/2','BackHeight')
    feature(b,'SolidBlank',s,'OuterDepth')
    fillet(b,'SoftTopCorners',edges_along_y(b.Shape,lambda e:e.CenterOfMass.z>91),6)
    s=rectangle(b,'CardCavity','-InnerWidth/2','Wall','InnerWidth/2','Wall+InnerDepth',
                orientation='XY',position=(0,0,p['BackHeight']+1))
    feature(b,'OpenPocket',s,'BackHeight+1 mm-Bottom',kind='Pocket',reversed=False)
    # Trimming a YZ profile leaves a continuous sloping rim and an open top.
    s=polygon(b,'SlopingSideRim',[
        ('Wall','BackHeight'),('Wall+InnerDepth','FrontHeight'),('OuterDepth+1 mm','FrontHeight'),
        ('OuterDepth+1 mm','BackHeight+2 mm'),('Wall','BackHeight+2 mm')],
        orientation='YZ',position=(-w/2-1,0,0))
    feature(b,'TrimRim',s,'OuterWidth+2 mm',kind='Pocket',reversed=True)
    s=rectangle(b,'FrontFingerOpening','-GripWidth/2','FrontGripHeight','GripWidth/2','BackHeight+4 mm',position=(0,depth+1,0))
    feature(b,'FrontScoop',s,'Wall+1 mm',kind='Pocket',reversed=True)
    fillet(b,'RoundFrontScoop',edges_along_y(b.Shape,lambda e:abs(e.CenterOfMass.z-p['FrontGripHeight'])<1e-4 and abs(abs(e.CenterOfMass.x)-p['GripWidth']/2)<1e-4),p['GripRadius'])
    s=rectangle(b,'RearFingerOpening','-GripWidth/2','RearGripHeight','GripWidth/2','BackHeight+4 mm',position=(0,-1,0))
    feature(b,'RearScoop',s,'Wall+1 mm',kind='Pocket',reversed=False)
    fillet(b,'RoundRearScoop',edges_along_y(b.Shape,lambda e:abs(e.CenterOfMass.z-p['RearGripHeight'])<1e-4 and abs(abs(e.CenterOfMass.x)-p['GripWidth']/2)<1e-4),p['GripRadius'])
    # Soften front-facing and inner mouth edges without rounding the wall's glue plane.
    edgeids=[]
    for i,e in enumerate(b.Shape.Edges,1):
        bb=e.BoundBox
        if (bb.YLength<1e-6 and abs(bb.YMin-depth)<1e-5) or (bb.YLength<1e-6 and abs(bb.YMin-p['Wall'])<1e-5 and bb.ZMin>70):
            edgeids.append(i)
    fillet(b,'TouchEdges',edgeids,0.6)
    # Integral stand-off rails keep the card's rear face 10.2 mm from the wall,
    # so a fingertip can reach behind its exposed top at the rear scoop.
    for name,x in [('Left',-65),('Right',65)]:
        s=rectangle(b,name+'StandOff',x-4,'Wall',x+4,'Wall+RearStandOff',orientation='XY',position=(0,0,p['Bottom']))
        feature(b,name+'RearRail',s,'70 mm-Bottom',reversed=False)
    topedges=[i for i,e in enumerate(b.Shape.Edges,1) if abs(e.CenterOfMass.z-70)<1e-5 and abs(e.CenterOfMass.y-p['Wall']-p['RearStandOff'])<1e-5 and e.BoundBox.XLength>7.9]
    fillet(b,'SoftStandOffTops',topedges,0.8)
    panel_y=depth+p['GlueGap']
    b=body('SkyPanel')
    s=rectangle(b,'PanelOutline','-PanelWidth/2','PanelBottom','PanelWidth/2','PanelBottom+PanelHeight',position=(0,panel_y,0))
    feature(b,'PanelPlate',s,'PanelThickness')
    fillet(b,'PanelCorners',edges_along_y(b.Shape),5)
    s=circles(b,'ReelSeats',[(x,p['ReelZ'],p['ReelRadius']+p['ReelFitClearance']) for x in [-p['ReelX'],p['ReelX']]],position=(0,panel_y+p['PanelThickness']+0.1,0))
    feature(b,'OpenReelSeats',s,'PanelThickness+0.2 mm',kind='Pocket',reversed=True)
    # An open-through rounded smile shows the navy shell beneath it.
    s=polygon(b,'HappySmile',[(-12,24),(-9,20),(-5,18),(5,18),(9,20),(12,24),(10,25),(7,22),(4,21),(-4,21),(-7,22),(-10,25)],position=(0,panel_y+p['PanelThickness']+0.1,0))
    feature(b,'SmileWindow',s,'PanelThickness+0.2 mm',kind='Pocket',reversed=True)
    for name,x in [('ReelLeft',-p['ReelX']),('ReelRight',p['ReelX'])]:
        b=body(name)
        s=circles(b,name+'Outline',[(x,p['ReelZ'],p['ReelRadius']),(x,p['ReelZ'],p['ReelHoleRadius'])],position=(0,panel_y,0))
        feature(b,name+'Ring',s,'PanelThickness')
        import math
        holes=[(x+10*math.cos(a),p['ReelZ']+10*math.sin(a),1.25) for a in [math.pi/2,math.pi*7/6,math.pi*11/6]]
        s=circles(b,name+'SpoolWindows',holes,position=(0,panel_y+p['PanelThickness']+0.1,0))
        feature(b,name+'SpoolCutouts',s,'PanelThickness+0.2 mm',kind='Pocket',reversed=True)
    b=body('TapeBadge')
    s=polygon(b,'TapeHeadOutline',[(-33,4.5),(33,4.5),(28,11.5),(-28,11.5)],position=(0,panel_y,0))
    feature(b,'TapeHeadPlate',s,'BadgeThickness')
    s=circles(b,'TapeScrews',[(-23,7.7,1.3),(23,7.7,1.3)],position=(0,panel_y+p['BadgeThickness']+0.1,0))
    feature(b,'TapeScrewWindows',s,'BadgeThickness+0.2 mm',kind='Pocket',reversed=True)
    b=body('MusicNote')
    note_y=panel_y+p['PanelThickness']+p['GlueGap']
    # One joined pair of beamed notes, with 2.6 mm stems for a durable separate print.
    s=polygon(b,'BeamedNotes',[
        (-11,32),(-11,35),(-9,37),(-5,37),(-5,50),(10,53),(10,35),
        (9,33),(6,32),(2,33),(2,36),(4,38),(7.4,38),(7.4,47),
        (-2.4,45),(-2.4,34),(-4,32),(-7,31)],position=(0,note_y,0))
    feature(b,'YellowNotes',s,'NoteThickness')
    # Native view providers are available when called by the offscreen GUI builder.
    for name,b in parts.items():
        rgb=spec['colors'][b.PrintColor].lstrip('#')
        color=tuple(int(rgb[i:i+2],16)/255 for i in (0,2,4))
        if b.ViewObject:
            b.ViewObject.ShapeColor=color
            b.Tip.ViewObject.ShapeColor=color
            b.Tip.ViewObject.LineColor=tuple(c*.65 for c in color)
            b.Tip.ViewObject.DisplayMode='Flat Lines'
            b.ViewObject.Visibility=True
    doc.recompute()
    return doc,parts
