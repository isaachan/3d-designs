"""Matched mating tapers with a separate constant-section socket end relief."""
from garage_bookshelf.geometry.sketches import loops
from garage_bookshelf.geometry.features import loft,finish
from garage_bookshelf.parameters import expression


def socket_end_relief(body,name,tip):
    f=body.newObject('PartDesign::Pocket',name+'EndRelief')
    f.Profile=tip
    f.setExpression('Length',expression('SocketDepth-TongueLength'))
    f.Reversed=True;f.Refine=True
    return finish(body,f)

def dovetail(body,name,kind,x,center,subtract=False):
    c='HalfClearance' if subtract else 'Zero'
    over='SocketOvercut' if subtract else 'Zero'
    length=('SocketDepth' if subtract else 'TongueLength') if kind!='deck' else ('DeckSocketDepth' if subtract else 'DeckTongueLength')
    matched_socket=subtract and kind in ('base','back')
    if matched_socket:length='TongueLength'
    sections=[]
    for label in ('Root','Tip'):
        if kind in ('base','deck'):
            prefix='Base' if kind=='base' else 'Deck'
            bot=f'{prefix}{label}Bottom+{c}';top=f'{prefix}{label}Top+{c}'
            height='BaseThickness' if kind=='base' else 'DeckThickness'
            points=[(f'{center}-({bot})',f'-{over}'),(f'{center}+({bot})',f'-{over}'),(f'{center}+({top})',f'{height}+{over}'),(f'{center}-({top})',f'{height}+{over}')]
        else:
            front=f'BackFront-BackFrontOverlap-{c}';rear=f'BackRear+{c}'
            fh=f'Back{label}Front+{c}';rh=f'Back{label}Rear+{c}'
            points=[(front,f'{center}-({fh})'),(front,f'{center}+({fh})'),(rear,f'{center}+({rh})'),(rear,f'{center}-({rh})')]
        xx=x if label=='Root' else f'{x}+{length}'
        sections.append(loops(body,name+'_'+label,[points],orientation='YZ',offset=(xx,'Zero','Zero')))
    result=loft(body,name,sections[0],sections[1],subtract=subtract)
    return socket_end_relief(body,name,sections[1]) if matched_socket else result
