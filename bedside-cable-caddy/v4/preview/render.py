"""Render the delivered braced STL at the wall."""

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "preview"))
from render import box, lamp, material, photograph, stage


scene = stage(HERE.parent / "printing/bedside-braced-box.stl")
wall = material("Warm painted wall", (0.60, 0.53, 0.43), 0.77, True)
box("Wall", (0, -0.014, 0.075), (3, 0.025, 3), wall)
lamp("Window", (-0.27, 0.23, 0.41), (0, 0.05, 0.10), 22, 0.26, (1, 0.93, 0.84))
lamp("Front fill", (0.24, 0.30, 0.18), (0, 0.05, 0.05), 12, 0.22, (0.80, 0.90, 1))
photograph(scene, HERE / "braced-box.png", (0.33, 0.42, 0.25), (0, 0.046, 0.083), 0.305)
