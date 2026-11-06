"""Render additional camera angles from an existing CAD-derived Blender scene.

Blender --background --python tools/render_angles.py -- --input <scene.blend>
  --angle front|opposite|top --output build/<new-run>/<angle>.png
Only cameras/render settings change; source geometry and materials stay intact.
"""
import argparse
from pathlib import Path
import sys
import bpy
from mathutils import Vector

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--input',required=True,type=Path)
parser.add_argument('--angle',required=True,choices=['front','opposite','top'])
parser.add_argument('--output',required=True,type=Path)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
root=Path(__file__).resolve().parents[1]
out=args.output.resolve()
if not out.is_relative_to(root/'build') or out.exists():
    parser.error('Use a new PNG file under this project build/.')
out.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(args.input.resolve()))
scene=bpy.context.scene;camera=scene.camera
views={
    'front':((0,7,.57),(0,.15,.57),2.35),
    'opposite':((-3.3,6,3.0),(0,.15,.57),2.6),
    'top':((.7,4.5,6.5),(0,.16,.48),2.55),
}
location,target,scale=views[args.angle]
camera.location=location
camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.type='ORTHO';camera.data.ortho_scale=scale
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.render.threads_mode='FIXED';scene.render.threads=6
scene.render.resolution_x=1600;scene.render.resolution_y=1120;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.filepath=str(out)
bpy.ops.render.render(write_still=True)
print('RENDERED',out,flush=True)
