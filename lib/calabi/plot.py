# Renders Grasshopper redundant, simply execute this script from Rhino > RunPythonScript
# @see http://www.tanjiasi.com/surface-design/
# @see http://www.grasshopper3d.com/video/calabi-yau-manifold-in-grasshopper
# @todo Replace float with cmath.exp for extended floating point precision

import importlib
import cmath
from math import cos, sin, pi
import rhinoscriptsyntax as rs
import scriptcontext
import System.Guid
import Rhino.Geometry.Point3d as Point3d
import Rhino.Geometry.Mesh as Mesh
import Rhino.Collections.Point3dList as Point3dList

# Import local modules
import export

# Dimensions of Calabi Yau Manifold [1..10]
n       = rs.GetInteger("n", 1, 1)
# Degree [0.0..1.0]
Degree  = rs.GetReal("Degree", 1.0, 1.0)
# Density multiplier
Density = float(rs.GetReal("Density", 0.1, 0.001))
Alpha   = (float(Degree) + 1) * pi
I       = complex(0.0, 1.0)

# @return [Rhino.Collections.Point3dList]
Points = Point3dList()
Meshes = [] # Rhino.Collections.MeshFaceList

def qrange(start, stop = None, step = 1):
    # if start is missing it defaults to zero, somewhat tricky
    start, stop = (0, start) if stop is None else (start, stop)
    # allow for decrement
    while start > stop if step < 0 else start < stop:
        yield start # makes this a generator for new start value
        start += step

def Complex_u1(a, b):
    m1    = complex(a, b)
    m2    = complex(-a, -b)
    m1Exp = cmath.exp(m1)
    m2Exp = cmath.exp(m2)
    m1Exp_Plus_m2Exp = m1Exp + m2Exp
    return m1Exp_Plus_m2Exp * 0.5

def Complex_u2(a, b):
    m1    = complex(a, b)
    m2    = complex(-a, -b)
    m1Exp = cmath.exp(m1)
    m2Exp = cmath.exp(m2)
    m1Exp_Plus_m2Exp = m1Exp + m2Exp
    return m1Exp_Plus_m2Exp * 0.5

def Complex_z1(a, b, n, k):
    u_1 = Complex_u1(a, b) * (2.0 / n)
    m_1 = I * ((2.0 * pi * k) / n)
    m1  = cmath.exp(m_1)
    return m1 * u_1

def Complex_z2(a, b, n, k):
    u_2 = Complex_u2(a, b) * (2.0 / n)
    m_2 = I * ((2.0 * pi * k) / n)
    m2  = cmath.exp(m_2)
    return m2 * u_2


def Complex_z2(a, b, n, k):
    u_2 = Complex_u2(a, b) * (2.0 / n)
    m_2 = I * ((2.0 * pi * k) / n)
    m2  = cmath.exp(m_2)
    return m2 * u_2

# @param [float] step
#   Control points density
# @param [float] scale
def ParametricPlot3D(step, scale = 1):
    # num1  = step
    num2  = 0
    num3  = 0
    maxA  = 1
    maxB  = (pi / 2)
    stepB = maxB * step

    mesh = Mesh()

    for k1 in range(n):
        # print 'k1 ' + str(k1)

        for k2 in range(n):
            # print 'k2 ' + str(k2)

            for a in qrange(-1, maxA, step):
                # print 'a ' + str(a)

                for b in qrange(0, maxB, stepB):
                    # print 'b ' + str(b)

                    if a == -1 and k1 == 0 and k2 == 0:
                        num2 += 1

                    z1 = Complex_z1(a, b, n, k1)
                    z2 = Complex_z2(a, b, n, k2)

                    # @todo They multiply `x`, `y`, `z` by `num`. Why?
                    x = scale * (z1.real)
                    y = scale * (z2.real)
                    z = scale * ((cos(Alpha) * z1.imag + sin(Alpha) * z2.imag))

                    Points.Add(Point3d(x, y, z))

                    if a > -1:
                        if b > 0:
                            subMesh = Mesh()

                            AppendVertex(num3, subMesh)            # 0
                            # print 'Vert1: ' + str(num3)
                            AppendVertex(num3 - 1, subMesh)        # -1
                            # print 'Vert2: ' + str(num3 - 1)
                            AppendVertex(num3 - num2 - 1, subMesh) # -1 || -2
                            # print 'Vert3: ' + str(num3 - num2 - 1)
                            AppendVertex(num3 - num2, subMesh)     # 0 || -1
                            # print 'Vert4: ' + str(num3 - num2)

                            subMesh.Faces.AddFace(0, 1, 2, 3)
                            # subMesh.Normals.ComputeNormals()
                            # subMesh.Compact()
                            mesh.Append(subMesh)

                    # Increment position in `Points` array
                    num3 += 1

            # Join `mesh` Faces
            # mesh.Weld(360)
            # Add to Meshes
            Meshes.append(mesh)
            # And reset
            mesh = Mesh()

    return Meshes

# @param [Integer] i
# @param [Rhino.Geometry.Mesh] mesh
def AppendVertex(i, mesh):
    try:
        p = Points[i]
        mesh.Vertices.Add(p.X, p.Y, p.Z)
    except: # IndexError
        print 'Points[' + str(i) + '] out of range'
        return

def RenderPoints():
    for point in Points:
        rs.AddPoint(point)

def RenderMesh():
    for mesh in Meshes:
        # rs.AddMesh(mesh)
        if scriptcontext.doc.Objects.AddMesh(mesh) != System.Guid.Empty:
            scriptcontext.doc.Views.Redraw()

def Run(r = 1):
    ParametricPlot3D(Density, scale = 100)
    RenderMesh() if r == 1 else RenderPoints()

rs.EnableRedraw(True);

if __name__ == "__main__":
    Run()
