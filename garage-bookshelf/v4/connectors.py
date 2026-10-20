"""Two-section trapezoids preserve the source design's taper in both axes."""
from geometry.sketches import loops
from geometry.features import loft

def dovetail(body,name,kind,x,center,subtract=False):
    c='HalfClearance' if subtract else 'Zero'
    over='SocketOvercut' if subtract else 'Zero'
    length=('SocketDepth' if subtract else 'TongueLength') if kind!='deck' else ('DeckSocketDepth' if subtract else 'DeckTongueLength')
    sections=[]
    for label in ('Root','Tip'):
        if kind in ('base','deck'):
            prefix='Base' if kind=='base' else 'Deck'
            bot=f'{prefix}{label}Bottom+{c}';top=f'{prefix}{label}Top+{c}'
            height='BaseThickness' if kind=='base' else 'DeckThickness'
            points=[(f'{center}-({bot})',f'-{over}'),(f'{center}+({bot})',f'-{over}'),(f'{center}+({top})',f'{height}+{over}'),(f'{center}-({top})',f'{height}+{over}')]
        else:
            front=f'BackFront-BackFrontOverlap-{c}';rear=f'OverallDepth+{c}'
            fh=f'Back{label}Front+{c}';rh=f'Back{label}Rear+{c}'
            points=[(front,f'{center}-({fh})'),(front,f'{center}+({fh})'),(rear,f'{center}+({rh})'),(rear,f'{center}-({rh})')]
        xx=x if label=='Root' else f'{x}+{length}'
        sections.append(loops(body,name+'_'+label,[points],orientation='YZ',offset=(xx,'Zero','Zero')))
    return loft(body,name,sections[0],sections[1],subtract=subtract)
