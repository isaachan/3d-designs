"""Render the delivered STL on its own and in a schematic wall installation."""

import math
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
STL = HERE.parent / "printing/bedside-cable-caddy.stl"


def material(name, rgb, roughness=0.38, microtexture=False):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*rgb, 1)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    shader = nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*rgb, 1)
    shader.inputs["Roughness"].default_value = roughness
    if microtexture:
        tex_coord = nodes.new("ShaderNodeTexCoord")
        noise = nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 320
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.22
        bump.inputs["Distance"].default_value = 0.00010
        links = mat.node_tree.links
        links.new(tex_coord.outputs["Generated"], noise.inputs["Vector"])
        links.new(noise.outputs["Fac"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    return mat


def box(name, center, size, mat, radius=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    if radius:
        bevel = obj.modifiers.new("Edge radius", "BEVEL")
        bevel.width = radius
        bevel.segments = 5
        for face in obj.data.polygons:
            face.use_smooth = True
        obj.modifiers.new("Weighted normals", "WEIGHTED_NORMAL")
    return obj


def cable(name, points, radius, mat):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 24
    curve.bevel_depth = radius
    curve.bevel_resolution = 5
    curve.use_fill_caps = True
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for point, location in zip(spline.bezier_points, points):
        point.co = location
        point.handle_left_type = point.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)


def lamp(name, location, target, energy, size, color):
    bpy.ops.object.light_add(type="AREA", location=location)
    lamp = bpy.context.object
    lamp.name = name
    lamp.rotation_euler = (Vector(target) - lamp.location).to_track_quat("-Z", "Y").to_euler()
    lamp.data.energy = energy
    lamp.data.shape = "DISK"
    lamp.data.size = size
    lamp.data.color = color


def print_model(stl=STL, location=(0, 0, 0), name="Bedside cable caddy · manufacturing STL"):
    bpy.ops.wm.stl_import(filepath=str(stl), global_scale=0.001)
    caddy = bpy.context.object
    caddy.name = name
    caddy.location = location
    caddy.data.materials.append(material("Muted eucalyptus PETG", (0.044, 0.139, 0.112), 0.41, True))
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(32))
    return caddy


def stage(stl=STL):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    print_model(stl)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 32
    scene.cycles.use_denoising = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.resolution_x = 1440
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.world.use_nodes = True
    world = scene.world.node_tree.nodes.get("Background")
    world.inputs["Color"].default_value = (0.52, 0.59, 0.63, 1)
    world.inputs["Strength"].default_value = 0.33
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = -0.6
    return scene


def photograph(scene, filename, position, aim, scale):
    bpy.ops.object.camera_add(location=position)
    camera = bpy.context.object
    camera.rotation_euler = (Vector(aim) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = scale
    scene.camera = camera
    scene.render.filepath = str(HERE / filename)
    bpy.ops.render.render(write_still=True)


def hero():
    scene = stage()
    floor = material("Warm plaster", (0.56, 0.49, 0.39), 0.62)
    box("Studio sweep", (0, 0, -0.013), (4, 4, 0.0258), floor)
    lamp("Large warm softbox", (-0.16, 0.19, 0.35), (0, 0.03, 0.025), 20, 0.28, (1, 0.91, 0.78))
    lamp("Cool fill", (0.24, 0.26, 0.19), (0, 0.04, 0.04), 7, 0.23, (0.76, 0.87, 1))
    lamp("Rear rim", (0.13, -0.23, 0.27), (0, 0, 0.05), 16, 0.20, (1, 0.96, 0.84))
    photograph(scene, "product.png", (-0.24, 0.43, 0.60), (0, 0.029, 0.043), 0.273)


def installation():
    scene = stage()
    plaster = material("Painted wall", (0.65, 0.57, 0.45), 0.82, True)
    graphite = material("Charcoal outlet faceplate", (0.032, 0.041, 0.042))
    ivory = material("Porcelain adapters", (0.8, 0.78, 0.72), 0.27)
    black = material("Graphite adapter and cable", (0.018, 0.024, 0.027), 0.43)
    silver = material("Connector shells", (0.34, 0.38, 0.41), 0.24)

    box("Wall", (0, -0.013, 0), (3, 0.024, 3), plaster)
    box("Outlet faceplate", (0.053, 0.0025, 0.165), (0.136, 0.007, 0.052), graphite, 0.003)
    box("Wall USB power adapter", (0.019, 0.020, 0.164), (0.029, 0.031, 0.028), ivory, 0.003)
    box("Angled AC plug", (0.101, 0.015, 0.165), (0.025, 0.019, 0.023), black, 0.003)
    box("Inline laptop power brick", (0.042, 0.032, 0.021), (0.084, 0.037, 0.031), black, 0.004)
    box("Spare USB adapter", (-0.054, 0.029, 0.022), (0.035, 0.033, 0.033), ivory, 0.004)
    for x in (-0.060, -0.048):
        box("Spare adapter prong", (x, 0.029, 0.044), (0.003, 0.0016, 0.014), silver, 0.0006)

    cable("Mains to inline brick", [
        (0.106, 0.023, 0.160), (0.123, 0.033, 0.142), (0.128, 0.033, 0.104),
        (0.118, 0.024, 0.073), (0.103, 0.021, 0.065), (0.092, 0.024, 0.054),
        (0.090, 0.033, 0.033), (0.084, 0.035, 0.022),
    ], 0.0022, black)
    cable("Laptop lead through right front notch", [
        (0.019, 0.049, 0.022), (0.030, 0.050, 0.025), (0.049, 0.052, 0.039),
        (0.061, 0.062, 0.037), (0.068, 0.081, 0.024), (0.077, 0.105, -0.022),
        (0.091, 0.118, -0.061),
    ], 0.0019, black)
    cable("Phone lead through left front notch", [
        (0.019, 0.035, 0.162), (0.017, 0.048, 0.150), (-0.006, 0.047, 0.124),
        (-0.043, 0.044, 0.103), (-0.072, 0.040, 0.063), (-0.077, 0.046, 0.023),
        (-0.070, 0.051, 0.024), (-0.061, 0.059, 0.038), (-0.061, 0.071, 0.036),
        (-0.060, 0.084, 0.009), (-0.065, 0.096, -0.028),
    ], 0.00155, ivory)
    for x, y, z, mat in [(-0.065, 0.096, -0.030, ivory), (0.091, 0.118, -0.063, black)]:
        box("Cable connector", (x, y, z), (0.007, 0.0045, 0.011), mat, 0.001)
        box("USB-C shell", (x, y, z - 0.007), (0.006, 0.003, 0.005), silver, 0.0007)

    cable("Stored watch charging cable", [
        (-0.020, 0.021, 0.013), (-0.041, 0.027, 0.010), (-0.038, 0.050, 0.012),
        (-0.016, 0.051, 0.016), (-0.004, 0.037, 0.014), (-0.014, 0.019, 0.012),
        (-0.029, 0.023, 0.013), (-0.027, 0.038, 0.017), (-0.013, 0.049, 0.029),
        (0.000, 0.062, 0.036), (0.003, 0.077, 0.029), (0.005, 0.091, -0.006),
    ], 0.00125, ivory)
    box("Watch cable connector", (0.005, 0.091, -0.009), (0.0065, 0.0038, 0.010), ivory, 0.001)
    box("Watch cable USB-C shell", (0.005, 0.091, -0.015), (0.0058, 0.0028, 0.004), silver, 0.0006)
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=0.011, depth=0.004,
                                       location=(-0.014, 0.022, 0.008))
    bpy.context.object.name = "Watch charging puck"
    bpy.context.object.data.materials.append(ivory)

    lamp("Window", (-0.22, 0.22, 0.37), (0, 0.02, 0.065), 28, 0.31, (1, 0.91, 0.80))
    lamp("Room fill", (0.23, 0.36, 0.19), (0, 0.03, 0.075), 10, 0.26, (0.85, 0.92, 1))
    photograph(scene, "wall-use.png", (-0.28, 0.64, 0.40), (0.006, 0.018, 0.064), 0.394)


if __name__ == "__main__":
    hero()
    installation()
