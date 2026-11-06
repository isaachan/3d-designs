"""Render exported CAD triangles in Blender, with illustrative cards/tape only.

Blender --background --python tools/render.py -- --scene build/<run>/scene.json
"""
import argparse
import json
from pathlib import Path
import math
import sys
import bpy
from mathutils import Vector

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--scene',required=True,type=Path)
parser.add_argument('--view',choices=['hero','empty','rear'],default='hero')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
data=json.loads(args.scene.read_text()); spec=data['spec']; p=spec['dimensions_mm']
out=args.scene.parent/(args.view+'.png')
if out.exists(): raise FileExistsError(out)
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
scale=.01
def material(name,color,roughness=.38):
    mat=bpy.data.materials.new(name); mat.use_nodes=True
    rgb=[int(color[i:i+2],16)/255 for i in [1,3,5]] if isinstance(color,str) else color
    # Hex inputs are sRGB, while node colors are linear.
    rgb=[c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4 for c in rgb]
    bsdf=mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value=(*rgb,1)
    bsdf.inputs['Roughness'].default_value=roughness
    return mat
mats={name:material(name,color) for name,color in spec['colors'].items()}
paper=material('Ivory card stock','#FFFDF3',.67)
ink=material('Printed music','#385B7F',.8)
wallmat=material('Warm plaster','#EEEDE5',.9)
def cube(name,center,dimensions,mat,bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=[v*scale for v in center])
    obj=bpy.context.object; obj.name=name; obj.dimensions=[v*scale for v in dimensions]
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    obj.data.materials.append(mat)
    if bevel:
        mod=obj.modifiers.new('Soft manufactured edges','BEVEL');mod.width=bevel*scale;mod.segments=3
        obj.modifiers.new('Face normals','WEIGHTED_NORMAL')
    return obj
for obj in data['objects']:
    mesh=bpy.data.meshes.new(obj['name'])
    mesh.from_pydata([[v*scale for v in xyz] for xyz in obj['vertices']],[],obj['faces']);mesh.update()
    o=bpy.data.objects.new(obj['name'],mesh);bpy.context.collection.objects.link(o)
    o.data.materials.append(mats[obj['color']])
    for face in mesh.polygons: face.use_smooth=True
    mod=o.modifiers.new('Weighted face normals','WEIGHTED_NORMAL'); mod.keep_sharp=True; mod.weight=50

if args.view=='hero':
    # Count/score are illustrative, not inferred from the photo.
    start=p['Wall']+p['RearStandOff']+2.5
    n=20; thickness=p['StackDepth']/n
    for i in range(n):
        mat=paper if i==n-1 else [paper,mats['lightblue'],paper,mats['yellow'],paper][i%5]
        cube('Illustrative card '+str(i+1),(0,start+(i+.5)*thickness,p['Bottom']+p['CardHeight']/2),
             (p['CardWidth'],thickness-.035,p['CardHeight']),mat,.45)
    front_y=start+p['StackDepth']+.02
    # Front card's exposed strip: title and a few staff lines/notes.
    def text(body,x,z,size):
        curve=bpy.data.curves.new('Card title','FONT');curve.body=body;curve.size=size*scale
        curve.extrude=0;curve.space_character=1.05
        ob=bpy.data.objects.new('Printed '+body,curve);bpy.context.collection.objects.link(ob)
        ob.location=(x*scale,front_y*scale,z*scale);ob.rotation_euler=(math.pi/2,0,math.pi)
        ob.data.materials.append(ink)
    text('Sing a little song',76,95,5)
    text('MUSIC CARDS',-48,96,2.3)
    for z in [83,85,87,89,91]: cube('Printed staff',(0,front_y,z),(150,.03,.16),ink)
    for x,z in [(-57,87),(-39,89),(-21,85),(-3,87),(15,91),(33,89),(51,87)]:
        cube('Printed note stem',(x,front_y+.01,z+2.4),(.35,.05,5),ink)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,radius=1,location=(x*scale,front_y*scale,z*scale))
        o=bpy.context.object;o.name='Printed note head';o.scale=(1.1*scale,.025*scale,.7*scale);o.data.materials.append(ink)
elif args.view=='rear':
    adhesive=material('Illustrative adhesive liner','#FFD65B',.7)
    for x,z,width,height in spec['adhesive_zones_mm']:
        cube('Illustrative 20 x 60 mm tape landing',(x+width/2,-.45,z+height/2),(width,.9,height),adhesive,.9)

if args.view!='rear':
    cube('Wall',(0,-3,90),(500,5,330),wallmat)
cube('Studio floor',(0,30,-4),(2000,2000,6),wallmat)
scene=bpy.context.scene; scene.render.engine='CYCLES'
scene.cycles.samples=40;scene.cycles.use_denoising=True
scene.render.threads_mode='FIXED';scene.render.threads=8
scene.world.color=(.4,.4,.4)
scene.view_settings.view_transform='AgX'
def light(name,location,power,size):
    bpy.ops.object.light_add(type='AREA',location=location)
    obj=bpy.context.object;obj.name=name;obj.data.energy=power;obj.data.shape='DISK';obj.data.size=size
    obj.rotation_euler=(Vector((0,0,.6))-obj.location).to_track_quat('-Z','Y').to_euler()
light('Softbox key',(-3,4,5),450,4)
light('Softbox fill',(4,2,3),220,3)
light('Top rim',(-1,-2,5),250,2.5)
bpy.ops.object.camera_add()
camera=bpy.context.object;scene.camera=camera
if args.view=='rear': location=(2.5,-5.5,2.8);target=(0,.12,.48)
elif args.view=='empty': location=(2.8,5.4,3.5);target=(0,.13,.47)
else: location=(2.8,6.5,3.4);target=(0,.14,.57)
camera.location=location;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.type='ORTHO';camera.data.ortho_scale=2.65
scene.render.resolution_x=1600;scene.render.resolution_y=1120;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.filepath=str(out.resolve())
bpy.ops.wm.save_as_mainfile(filepath=str((args.scene.parent/(args.view+'.blend')).resolve()))
bpy.ops.render.render(write_still=True)
print('RENDERED',out,flush=True)
