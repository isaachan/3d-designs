"""Show how the three printed components sit against the wall."""

from pathlib import Path
import sys

import bpy
from mathutils import Matrix

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "preview"))
from render import box, lamp, material, photograph, stage


scene = stage(HERE.parent / "printing/bedside-rapid-box.stl")
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.separate(type="LOOSE")
bpy.ops.object.mode_set(mode="OBJECT")
parts = [obj for obj in scene.objects if obj.type == "MESH"]
assert len(parts) == 3
braces = sorted((obj for obj in parts if min(v[1] for v in obj.bound_box) > 104),
                key=lambda obj: min(v[0] for v in obj.bound_box))
assert len(braces) == 2
for brace, center, offset in zip(braces, (-0.047, 0.047), (-0.085, 0.009)):
    brace.matrix_world = Matrix((
        (0, 0, -1, center + 0.005),
        (1, 0, 0, -offset),
        (0, -1, 0, 0.108),
        (0, 0, 0, 1),
    )) @ Matrix.Scale(0.001, 4)
    brace.data.materials.clear()
    brace.data.materials.append(material("Teal brace", (0.034, 0.107, 0.085), 0.44))
wall = material("Painted wall", (0.60, 0.53, 0.43), 0.77, True)
box("Wall", (0, -0.014, 0.075), (3, 0.025, 3), wall)
lamp("Window", (-0.27, 0.23, 0.41), (0, 0.05, 0.08), 22, 0.26, (1, 0.93, 0.84))
lamp("Front fill", (0.24, 0.30, 0.18), (0, 0.05, 0.04), 12, 0.22, (0.80, 0.90, 1))
lamp("Lower fill", (-0.20, 0.24, -0.10), (0, 0.04, -0.015), 7, 0.22, (0.94, 0.97, 1))
photograph(scene, HERE / "assembled.png", (0.39, 0.45, 0.061), (0, 0.046, 0.039), 0.286)
