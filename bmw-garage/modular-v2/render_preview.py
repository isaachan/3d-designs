"""Blender background renderer. Input is generated/preview-meshes.json (temporary)."""
from pathlib import Path
import bpy, json
from mathutils import Vector
ROOT=Path(__file__).resolve().parent/'generated'
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
for entry in json.loads((ROOT/'preview-meshes.json').read_text()):
    mesh=bpy.data.meshes.new(entry['name']); mesh.from_pydata(entry['vertices'],[],entry['faces']); mesh.update()
    obj=bpy.data.objects.new(entry['name'],mesh); bpy.context.collection.objects.link(obj)
    # Preview-only 0.015 mm offset prevents depth-buffer fighting on flush colored faces.
    if entry.get('color')!=entry.get('base_color'):
        p=entry.get('plate')
        obj.location=(.015,0,0) if p==3 else (0,-.015,0) if p==4 else (0,0,.015)
    mat=bpy.data.materials.new(entry['name']); mat.diffuse_color=tuple(entry['rgba']); obj.data.materials.append(mat)
bpy.ops.object.camera_add(location=(290,-380,285))
cam=bpy.context.object; direction=Vector((0,0,43))-cam.location
cam.rotation_euler=direction.to_track_quat('-Z','Y').to_euler(); cam.data.type='ORTHO'; cam.data.ortho_scale=345
scene=bpy.context.scene; scene.camera=cam
scene.render.engine='BLENDER_WORKBENCH'
shade=scene.display.shading; shade.light='STUDIO'; shade.color_type='MATERIAL'; shade.show_shadows=True; shade.show_cavity=True
shade.cavity_type='BOTH'; shade.curvature_ridge_factor=1.1; shade.curvature_valley_factor=1.0
shade.show_specular_highlight=True; shade.background_type='WORLD'; scene.world.color=(.85,.88,.92)
scene.render.resolution_x=1800; scene.render.resolution_y=1500; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'; scene.render.filepath=str(ROOT/'assembly-cutaway.png')
scene.view_settings.view_transform='Standard'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'assembly-cutaway.blend'))
bpy.ops.render.render(write_still=True)
