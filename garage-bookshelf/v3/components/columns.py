from geometry.sketches import circle
from geometry.features import pad,loft

def build(body):
    pad(body,'Pad_Shaft',circle(body,'Sketch_Shaft','ColumnRadius','Zero'),'ColumnHeight')
    for i in (1,2,3):
        top=f'DeckZ{i}-BaseThickness'
        bottom=f'{top}-CollarThickness-ConeHeight'
        root=circle(body,f'Sketch_Cone{i}_Root','ColumnRadius',bottom)
        tip=circle(body,f'Sketch_Cone{i}_Tip','CollarRadius',f'{top}-CollarThickness')
        loft(body,f'Loft_Cone{i}',root,tip)
        pad(body,f'Pad_Collar{i}',circle(body,f'Sketch_Collar{i}','CollarRadius',f'{top}-CollarThickness'),'CollarThickness')
    return body
