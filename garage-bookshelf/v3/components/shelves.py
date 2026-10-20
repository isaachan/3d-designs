from geometry.sketches import rectangle,loops
from geometry.features import pad,pocket
from components.connectors import dovetail

def build(body,right):
    pad(body,'Pad_Deck',rectangle(body,'Sketch_Deck','DeckHalfWidth','DeckDepth'),'DeckThickness')
    x='DeckNotchX';xx='DeckNotchX+DeckNotchWidth';z='DeckThickness'
    loops_=[[(x,'Zero'),(xx,'Zero'),(xx,'DeckFrontNotchDepth'),(x,'DeckFrontNotchDepth')],[(x,'DeckRearNotchStart'),(xx,'DeckRearNotchStart'),(xx,'DeckDepth'),(x,'DeckDepth')]]
    pocket(body,'Pocket_EdgeNotches',loops(body,'Sketch_EdgeNotches',loops_,offset=('Zero','Zero',z)),z)
    for i in (1,2): dovetail(body,f'{"Socket" if right else "Tongue"}_{i}','deck','-Overlap' if right else 'DeckHalfWidth-Overlap',f'DeckJointY{i}',right)
    return body
