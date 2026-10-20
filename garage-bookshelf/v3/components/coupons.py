from geometry.sketches import rectangle
from geometry.features import pad
from components.connectors import dovetail
from components.modules import build as module

def build(body,kind,male):
    if kind=='corner':
        return module(body,1 if male else 5,width='CouponWidth',origin='Zero',coupon=True)
    if kind=='base':
        s=rectangle(body,'Sketch_Base','CouponWidth','CouponDepth');length='BaseThickness';center='CouponBaseY'
    else:
        s=rectangle(body,'Sketch_Back','CouponWidth','BackThickness',origin=('Zero','BackFront'),offset=('Zero','Zero','BaseThickness'));length='CouponBackHeight';center='CouponBackZ'
    pad(body,'Pad_Base',s,length)
    dovetail(body,'Tongue' if male else 'Socket',kind,'CouponWidth-Overlap' if male else '-Overlap',center,not male)
    return body
