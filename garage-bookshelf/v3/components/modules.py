from geometry.sketches import rectangle,loops
from geometry.features import pad
from components.connectors import dovetail

def build(body,index,width=None,origin=None,removed='Zero',coupon=False):
    width=width or f'ModuleWidth{index}'
    origin=origin or f'ModuleStart{index}'
    pad(body,'Pad_Base',rectangle(body,'Sketch_Base',width,'OverallDepth'),'BaseThickness')
    pad(body,'Pad_Back',rectangle(body,'Sketch_Back',width,'BackThickness',origin=('Zero','BackFront'),offset=('Zero','Zero','WallStart')),'WallPadLength')
    if not coupon and index in (2,5):
        px=f'{"DividerX" if index==2 else "RightWallX"}-{origin}-{removed}'
        pad(body,'Pad_Upright',rectangle(body,'Sketch_Upright','WallThickness','PanelDepth',origin=(px,'Zero'),offset=('Zero','Zero','WallStart')),'WallPadLength')
        root=f'{px}+WallThickness-Overlap' if index==2 else f'{px}+Overlap'
        tip=f'{root}+RibSize' if index==2 else f'{root}-RibSize'
        for i,y in enumerate(('RibFrontY','RibRearY'),1):
            tri=[(root,'WallStart'),(tip,'WallStart'),(root,'WallStart+RibSize')]
            if index==5 and removed!='Zero':
                # Source deletion at X900 clips the rib's low tail; retaining a full
                # triangle after shortening would add 561.8mm³ of material.
                cut='NarrowCutFrom5'
                tri=[(root,'WallStart'),(cut,'WallStart'),(cut,f'WallStart+RibSize-(({root})-{cut})'),(root,'WallStart+RibSize')]
            # XZ sketch has normal -Y; sketch at far face extrudes toward near face.
            s=loops(body,f'Sketch_Rib{i}',[tri],orientation='XZ',offset=('Zero',f'{y}+RibThickness','Zero'))
            pad(body,f'Pad_Rib{i}',s,'RibThickness')
    if index<5:
        for i in (1,2):dovetail(body,f'BaseTongue{i}','base',f'{width}-Overlap',f'BaseJointY{i}')
        for i in (1,2):dovetail(body,f'BackTongue{i}','back',f'{width}-Overlap',f'BackJointZ{i}')
    if index>1:
        for i in (1,2):dovetail(body,f'BaseSocket{i}','base','-Overlap',f'BaseJointY{i}',True)
        for i in (1,2):dovetail(body,f'BackSocket{i}','back','-Overlap',f'BackJointZ{i}',True)
    return body
