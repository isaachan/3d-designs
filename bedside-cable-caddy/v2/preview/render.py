"""Render the V2 STL, including three oval coils in the stacked installation."""

import math
from pathlib import Path
import sys

import bpy

HERE = Path(__file__).resolve().parent
STL = HERE.parent / "printing/bedside-cable-tray.stl"
sys.path.insert(0, str(HERE.parents[1] / "preview"))
from render import box, cable, lamp, material, photograph, print_model, stage

UPPER = 0.211
POCKET_CENTERS = (-0.076133333, 0, 0.076133333)


def coil(x, diameter, turns, mat, tie):
    """An oval helix with turns stacking front-to-back."""
    radius = 0.030
    half_straight = 0.022
    z = 0.0036 + diameter / 2 + radius + half_straight + 0.0006
    rear = 0.0105
    pitch = diameter + 0.00045
    arc_half = math.pi * radius / 2
    straight = 2 * half_straight
    perimeter = 4 * arc_half + 2 * straight

    def section(s):
        if s < arc_half:
            angle = math.pi / 2 + s / radius
            return radius * math.cos(angle), half_straight + radius * math.sin(angle)
        s -= arc_half
        if s < straight:
            return -radius, half_straight - s
        s -= straight
        if s < 2 * arc_half:
            angle = math.pi + s / radius
            return radius * math.cos(angle), -half_straight + radius * math.sin(angle)
        s -= 2 * arc_half
        if s < straight:
            return radius, -half_straight + s
        s -= straight
        angle = s / radius
        return radius * math.cos(angle), half_straight + radius * math.sin(angle)

    curve = bpy.data.curves.new("Oval cable bundle", "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = diameter / 2
    curve.bevel_resolution = 4
    spline = curve.splines.new("POLY")
    samples = 96 * turns
    spline.points.add(samples)
    for index, point in enumerate(spline.points):
        fraction = index / 96
        u, v = section(perimeter * (fraction % 1))
        point.co = (x + u, rear + pitch * fraction, z + v, 1)
    bundle = bpy.data.objects.new("Coil", curve)
    bpy.context.collection.objects.link(bundle)
    bundle.data.materials.append(mat)
    front = rear + pitch * turns
    box("Reusable fabric tie", (x + radius, (rear + front) / 2 - 0.001, z + 0.009),
        (diameter + 0.003, front - rear + diameter, 0.010), tie, 0.0018)
    return (x, rear, z + radius + half_straight), (x, front, z + radius + half_straight)


def empty():
    scene = stage(STL)
    floor = material("Warm studio floor", (0.58, 0.51, 0.40), 0.68)
    box("Studio sweep", (0, 0, -0.013), (3, 3, 0.0258), floor)
    lamp("Softbox", (-0.20, 0.27, 0.40), (0, 0.03, 0.065), 23, 0.28, (1, 0.91, 0.78))
    lamp("Cool fill", (0.25, 0.25, 0.20), (0, 0.04, 0.06), 7, 0.25, (0.76, 0.87, 1))
    lamp("Rim", (0.10, -0.25, 0.31), (0, 0.0, 0.08), 16, 0.22, (1, 0.96, 0.84))
    photograph(scene, HERE / "three-pockets.png", (-0.25, 0.42, 0.64), (0, 0.026, 0.053), 0.302)


def stacked():
    scene = stage(STL)
    scene.render.resolution_x = 1152
    scene.render.resolution_y = 1440
    print_model(location=(0, 0, UPPER), name="V1 vented power module")

    plaster = material("Warm painted wall", (0.60, 0.54, 0.44), 0.82, True)
    black = material("Charcoal cable", (0.013, 0.018, 0.021), 0.55)
    white = material("Ivory cable", (0.83, 0.81, 0.75), 0.53)
    sand = material("Sand cable", (0.47, 0.33, 0.19), 0.55)
    faceplate = material("Outlet faceplate", (0.025, 0.033, 0.037), 0.46)
    tie = material("Woven hook-and-loop tie", (0.105, 0.123, 0.117), 0.88, True)
    shell = material("Connector shell", (0.27, 0.31, 0.33), 0.27)

    box("Wall", (0, -0.013, 0.2), (3, 0.024, 3), plaster)
    box("Outlet faceplate", (0.018, 0.0025, 0.360), (0.187, 0.007, 0.048), faceplate, 0.003)
    for x, body in [(-0.052, white), (0.014, white), (0.081, black)]:
        box("Wall plug", (x, 0.020, 0.360), (0.026, 0.031, 0.028), body, 0.003)
    box("Inline laptop adapter", (0.045, 0.034, UPPER + 0.023),
        (0.087, 0.038, 0.034), black, 0.004)
    cable("AC feed into power tray", [
        (0.081, 0.034, 0.356), (0.101, 0.042, 0.347), (0.120, 0.031, 0.317),
        (0.114, 0.022, 0.289), (0.101, 0.021, 0.278), (0.092, 0.033, 0.251),
        (0.088, 0.035, 0.234),
    ], 0.0022, black)

    for x, upper_x, diameter, turns, mat, lead, hang in [
        (POCKET_CENTERS[0], -0.061, 0.0038, 9, white, -0.052, -0.042),
        (POCKET_CENTERS[1], 0, 0.0032, 7, sand, 0.014, -0.022),
        (POCKET_CENTERS[2], 0.061, 0.0055, 7, black, None, -0.063),
    ]:
        inlet, outlet = coil(x, diameter, turns, mat, tie)
        if lead is None:
            top_route = [(0.047, 0.052, 0.235), (0.053, 0.054, 0.245)]
        else:
            top_route = [(lead, 0.035, 0.356), (lead, 0.052, 0.337),
                         (upper_x - 0.013, 0.045, 0.276), (upper_x - 0.009, 0.049, 0.245)]
        cable("Supply-side tail", top_route + [
            (upper_x, 0.063, 0.249), (upper_x + 0.002, 0.076, 0.232),
            (x + 0.004, 0.076, 0.196), (x - 0.013, 0.048, 0.155),
            (x - 0.009, 0.011, 0.132), inlet,
        ], diameter / 2, mat)
        cable("Device-side tail", [
            outlet, (x + 0.008, outlet[1], outlet[2] - 0.002),
            (x + 0.008, 0.057, 0.080), (x, 0.062, 0.064),
            (x - 0.003, 0.076, 0.056), (x - 0.004, 0.083, 0.018),
            (x + 0.006, 0.092, hang),
        ], diameter / 2, mat)
        box("USB connector", (x + 0.006, 0.092, hang - 0.005), (0.009, 0.005, 0.013), mat, 0.001)
        box("USB-C tip", (x + 0.006, 0.092, hang - 0.013), (0.008, 0.003, 0.005), shell, 0.0006)

    lamp("Window", (-0.30, 0.34, 0.57), (0, 0.04, 0.18), 36, 0.38, (1, 0.92, 0.80))
    lamp("Room fill", (0.27, 0.37, 0.32), (0, 0.04, 0.15), 12, 0.30, (0.82, 0.93, 1))
    photograph(scene, HERE / "stacked-use.png", (-0.24, 0.82, 0.54), (0, 0.025, 0.153), 0.514)


if __name__ == "__main__":
    stacked()
    empty()
