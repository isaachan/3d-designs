"""Stable translated double-precision metrics avoid Mesh.Volume cancellation far from origin."""
import math

def mesh_volume(mesh):
    points,facets=mesh.Topology
    origin=mesh.BoundBox.Center
    def term(face):
        a,b,c=(points[i]-origin for i in face)
        return a.dot(b.cross(c))/6
    return abs(math.fsum(term(f) for f in facets))

def bounds(shape):
    b=shape.optimalBoundingBox() if hasattr(shape,'optimalBoundingBox') else shape.BoundBox
    return [b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax]
