#!/usr/bin/env python3
"""Render only the reopened delivery CAD's real BRep faces, not concept meshes."""
import math
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, '/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as App
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy
from PIL import Image, ImageDraw, ImageFont
import build as b

ROOT = Path(__file__).resolve().parent


def run():
    doc = App.openDocument(str(ROOT/'cad/parking-lot-v1-assembly.FCStd'))
    actors = []
    for obj in doc.Objects:
        if 'DeliveryVisible' not in obj.PropertiesList or not obj.DeliveryVisible:
            continue
        points, triangles = obj.Shape.tessellate(.12)
        pts = vtk.vtkPoints()
        for v in points:
            pts.InsertNextPoint(v.x, v.y, v.z)
        cells = vtk.vtkCellArray()
        for tri in triangles:
            cells.InsertNextCell(3)
            for i in tri:
                cells.InsertCellPoint(i)
        poly = vtk.vtkPolyData()
        poly.SetPoints(pts)
        poly.SetPolys(cells)
        normals = vtk.vtkPolyDataNormals()
        normals.SetInputData(poly)
        normals.SetFeatureAngle(35)
        normals.ConsistencyOn()
        normals.AutoOrientNormalsOn()
        normals.Update()
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(normals.GetOutput())
        a = vtk.vtkActor()
        a.SetMapper(mapper)
        p = a.GetProperty()
        p.SetColor(*obj.DesignColor[:3])
        p.SetAmbient(.35)
        p.SetDiffuse(.65)
        p.SetSpecular(.15)
        if obj.DesignRole in ('lettering', 'parking-mark', 'road-mark'):
            p.SetAmbient(.8)
            p.SetDiffuse(.2)
        actors.append((a, obj.DesignRole, np.array([[v.x, v.y, v.z] for v in points])))
    for mode in ('assembly', 'road', 'rear'):
        ren = vtk.vtkRenderer()
        ren.SetBackground(.972, .976, .978)
        ren.SetUseFXAA(True)
        selected = [row for row in actors if mode != 'road' or row[1] in ('road', 'curb', 'road-mark')]
        for actor, _, _ in selected:
            ren.AddActor(actor)
        cam = ren.GetActiveCamera()
        cam.ParallelProjectionOn()
        toward = np.array([-.50, -.83, .50]) if mode != 'rear' else np.array([.45, .85, .44])
        toward /= np.linalg.norm(toward)
        right = np.cross([0, 0, 1], toward)
        right /= np.linalg.norm(right)
        up = np.cross(toward, right)
        cloud = np.concatenate([row[2] for row in selected])
        projected = cloud@np.stack([right, up, toward], axis=1)
        lo, hi = projected.min(axis=0), projected.max(axis=0)
        center = (lo+hi)/2
        focal = center[0]*right+center[1]*up+center[2]*toward
        cam.SetFocalPoint(*focal)
        cam.SetPosition(*(focal+1500*toward))
        cam.SetViewUp(0, 0, 1)
        cam.SetParallelScale(max((hi[1]-lo[1])*.70, (hi[0]-lo[0])*.43))
        for pos, intensity in [((-250, -500, 900), .9), ((850, 100, 550), .5)]:
            light = vtk.vtkLight()
            light.SetLightTypeToSceneLight()
            light.SetPosition(*pos)
            light.SetFocalPoint(*focal)
            light.SetIntensity(intensity)
            ren.AddLight(light)
        win = vtk.vtkRenderWindow()
        win.SetOffScreenRendering(1)
        win.SetSize(1800, 1200)
        win.SetMultiSamples(8)
        win.AddRenderer(ren)
        ren.ResetCameraClippingRange()
        win.Render()
        capture = vtk.vtkWindowToImageFilter()
        capture.SetInput(win)
        capture.SetInputBufferTypeToRGB()
        capture.ReadFrontBufferOff()
        capture.Update()
        data = vtk_to_numpy(capture.GetOutput().GetPointData().GetScalars()).reshape(1200, 1800, 3)
        image = Image.fromarray(data[::-1])
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype('/System/Library/Fonts/Hiragino Sans GB.ttc', 37)
        small = ImageFont.truetype('/System/Library/Fonts/Hiragino Sans GB.ttc', 23)
        labels = dict(assembly='完整装配', road='连续道路与四层接入', rear='背面装配')
        draw.text((45, 27), f'Parking Lot · CAD v1 | {labels[mode]}', font=font, fill='#20323d')
        draw.text((45, 82), '直接读取交付 CAD 的实体曲面渲染 · 单位 mm', font=small, fill='#536674')
        draw.text((45, 1110), '四层 10 车位 · 70 mm 等宽单车道 · 63 mm 层距 · 18 个底侧安装盲孔', font=small, fill='#20323d')
        draw.text((45, 1150), '第一版装配 CAD；轨道打印切分、分片接头及实物试装待后续设计。', font=small, fill='#536674')
        image.save(ROOT/f'reports/{mode}-preview.png')
        win.Finalize()
        print(f'Rendered {mode}', flush=True)
    App.closeDocument(doc.Name)


if __name__ == '__main__':
    run()
