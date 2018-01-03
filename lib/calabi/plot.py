# Renders Grasshopper redundant, simply execute this script from Rhino >
# RunPythonScript
# @see http://www.tanjiasi.com/surface-design/
# @see http://www.grasshopper3d.com/video/calabi-yau-manifold-in-grasshopper

import importlib
import cmath
from math import cos, sin, pi
import rhinoscriptsyntax as rs
import scriptcontext
import System.Guid
from Rhino.Geometry import Point3d, Mesh
# from Rhino.Collections import Point3dList

# Import local modules
import export

'''
n : int
    [1..10]
    Dimensions of Calabi Yau Manifold
Degree : float
    [0.0..1.0]
Density : float
    Sample rate multiplier
Points : list<Rhino.Geometry.Point3d>
Meshes : list<Rhino.Geometry.Mesh>
'''

n = rs.GetInteger("n", 1, 1)
Alpha = rs.GetReal("Degree", 1.0, 0.0)
Density = float(rs.GetReal("Density", 0.1, 0.01))
Points = []
Meshes = []


def ComplexU1(a, b):
    m1 = cmath.exp(complex(a, b))
    m2 = cmath.exp(complex(-a, -b))
    return (m1 + m2) * 0.5


def ComplexU2(a, b):
    m1 = cmath.exp(complex(a, b))
    m2 = cmath.exp(complex(-a, -b))
    return (m1 - m2) * 0.5


def ComplexZ1(a, b, n, k):
    i = complex(0.0, 1.0)
    u1 = ComplexU1(a, b) ** (2.0 / n)
    m1 = cmath.exp(i * ((2.0 * pi * k) / n))
    return m1 * u1


def ComplexZ2(a, b, n, k):
    i = complex(0.0, 1.0)
    u2 = ComplexU2(a, b) ** (2.0 / n)
    m2 = cmath.exp(i * ((2.0 * pi * k) / n))
    return m2 * u2


def ParametricPlot3D(step, scale=1):
    '''
    Parameters
    ----------
    step : float
        Control points density
    scale : float
    '''
    i = int(0)
    k = int(0)
    maxA = float(1)
    maxB = float(pi / 2)
    stepB = maxB * step

    for k1 in range(n):
        for k2 in range(n):
            mesh = Mesh()

            for a in rs.frange(float(-1), maxA, step):
                for b in rs.frange(float(0), maxB, stepB):
                    if (a == -1 and k1 == 0 and k2 == 0):
                        k += 1

                    z1 = ComplexZ1(a, b, n, k1)
                    z2 = ComplexZ2(a, b, n, k2)

                    # Calculate point coords
                    x = scale * (z1.real)
                    y = scale * (z2.real)
                    z = scale * ((cos(Alpha) * z1.imag + sin(Alpha) * z2.imag))

                    Points.Add(Point3d(x, y, z))

                    if a > -1:
                        if b > 0:
                            subMesh = Mesh()

                            AppendVertex(i, subMesh)
                            AppendVertex(i - 1, subMesh)
                            AppendVertex(i - k - 1, subMesh)
                            AppendVertex(i - k, subMesh)

                            subMesh.Faces.AddFace(0, 1, 2, 3)
                            # subMesh.Normals.ComputeNormals()
                            # subMesh.Compact()
                            mesh.Append(subMesh)

                    # Increment position in `Points` array
                    i += 1

            # Join `mesh` Faces
            mesh.Weld(pi)
            # Add to Meshes
            Meshes.append(mesh)

    return Meshes


def AppendVertex(i, mesh):
    '''
    Parameters
    ----------
    i : int
    mesh : Rhino.Geometry.Mesh
    '''
    try:
        p = Points[i]
        mesh.Vertices.Add(p.X, p.Y, p.Z)
    except IndexError:
        print 'Points[' + str(i) + '] out of range'
        return


def RenderPoints():
    for point in Points:
        rs.AddPoint(point)


def RenderMesh():
    for mesh in Meshes:
        if scriptcontext.doc.Objects.AddMesh(mesh) != System.Guid.Empty:
            scriptcontext.doc.Views.Redraw()


def Run(r=1):
    ParametricPlot3D(Density, scale=100)
    if r == 1:
        RenderMesh()
    else:
        RenderPoints()


rs.EnableRedraw(True)

if __name__ == '__main__':
    Run()
