'''
Replaces Grasshopper workflow -- execute via `RunPythonScript`

[](http://www.tanjiasi.com/surface-design/)
[](http://www.food4rhino.com/app/calabi-yau-manifold)
[Python Standard Library - math](https://docs.python.org/2/library/math.html)
[Python Standard Library - cmath](https://docs.python.org/2/library/cmath.html)
'''

import importlib
import cmath
from math import cos, sin, pi
import rhinoscriptsyntax as rs
import scriptcontext
import System.Guid
from Rhino.Geometry import Point3d, Mesh, NurbsCurve
# from Rhino.Collections import Point3dList

# Import local modules
import export


class Builder:
    def __init__(self, cy):
        self.CalabiYau = cy

    def Before(self, *args):
        return

    def Build(self, *args):
        return

    def After(self, *args):
        return

    def Render(self, *args):
        return


class PointCloudBuilder(Builder):
    def __init__(self, cy):
        Builder.__init__(self, cy)
        self.CalabiYau = cy

    def Render(self):
        for point in self.CalabiYau.Points:
            rs.AddPoint(point)


class MeshBuilder(Builder):
    def __init__(self, cy):
        Builder.__init__(self, cy)
        self.CalabiYau = cy
        self.Mesh = None
        self.SubMesh = None

    def Before(self):
        self.Mesh = Mesh()

    def Build(self, *args):
        a, b, i, k = args

        if a > -1:
            if b > 0:
                self.SubMesh = Mesh()

                self.AppendVertex(i)
                self.AppendVertex(i - 1)
                self.AppendVertex(i - k - 1)
                self.AppendVertex(i - k)

                self.SubMesh.Faces.AddFace(0, 1, 2, 3)
                # self.SubMesh.Normals.ComputeNormals()
                # self.SubMesh.Compact()
                self.Mesh.Append(self.SubMesh)

    def After(self):
        self.Mesh.Weld(pi)
        self.CalabiYau.Meshes.append(self.Mesh)

    def Render(self):
        for mesh in self.CalabiYau.Meshes:
            if scriptcontext.doc.Objects.AddMesh(mesh) != System.Guid.Empty:
                scriptcontext.doc.Views.Redraw()

    def AppendVertex(self, i):
        '''
        Parameters
        ----------
        i : int
        '''
        try:
            p = self.CalabiYau.Points[i]
            self.SubMesh.Vertices.Add(p.X, p.Y, p.Z)
        except IndexError:
            print 'Points[' + str(i) + '] out of range'
            return


class SurfaceBuilder(Builder):
    def __init__(self, cy):
        Builder.__init__(self, cy)
        self.CalabiYau = cy


class CurveBuilder(Builder):
    def __init__(self, cy):
        Builder.__init__(self, cy)
        self.CalabiYau = cy

    def Render(self):
        # curve = NurbsCurve.Create(False, 1, self.CalabiYau.Points)
        # # surface = Rhino.Geometry.NurbsCurve.CreateFromPoints(pointslist, )
        #
        # if scriptcontext.doc.Objects.AddCurve(curve) != System.Guid.Empty:
        scriptcontext.doc.Views.Redraw()


class CalabiYau:
    '''
    Attributes
    ----------
    n : int
        [1..10]
        Dimensions of Calabi Yau Manifold
    i : complex
    Alpha : float
        [0.0..1.0]
        Rotation
    Step : float
        [0.01..0.1]
        Sample rate
    Scale : int
        [1..100]
    Points : list<Rhino.Geometry.Point3d>
    Meshes : list<Rhino.Geometry.Mesh>
    '''
    def __init__(self, n=int(1), deg=float(1.0), step=float(0.1), scale=int(1)):
        self.n = n
        self.I = complex(0.0, 1.0)
        self.Alpha = deg * pi
        self.Step = step
        self.Scale = scale
        self.Points = []
        self.Meshes = []
        self.Builder = {
            1: self.PointCloudBuilder,
            2: self.MeshBuilder,
            3: self.SurfaceBuilder,
            4: self.CurveBuilder
        }

    def __ops__(self, builder):
        return {
            'before': [builder.Before],
            'build': [builder.Build],
            'after': [builder.After],
            'render': builder.Render
        }

    def PointCloudBuilder(self):
        return self.__ops__(PointCloudBuilder(self))

    def MeshBuilder(self):
        return self.__ops__(MeshBuilder(self))

    def SurfaceBuilder(self):
        return self.__ops__(SurfaceBuilder(self))

    def CurveBuilder(self):
        return self.__ops__(CurveBuilder(self))

    def Build(self, output=2):
        '''
        output : int
            if output == 1: then generate Rhino.Geometry.Point
            elif output == 2: then generate Rhino.Geometry.Mesh
            elif output == 3: then generate Rhino.Geometry.Surface
            else:
                raise
        '''
        builder = self.Builder[output]()
        self.ParametricPlot3D(builder)
        builder['render']()

    def ComplexU1(self, a, b):
        m1 = cmath.exp(complex(a, b))
        m2 = cmath.exp(complex(-a, -b))
        return (m1 + m2) * 0.5

    def ComplexU2(self, a, b):
        m1 = cmath.exp(complex(a, b))
        m2 = cmath.exp(complex(-a, -b))
        return (m1 - m2) * 0.5

    def ComplexZ1(self, a, b, n, k):
        u1 = self.ComplexU1(a, b) ** (2.0 / n)
        m1 = cmath.exp(self.I * ((2.0 * pi * k) / n))
        return m1 * u1

    def ComplexZ2(self, a, b, n, k):
        u2 = self.ComplexU2(a, b) ** (2.0 / n)
        m2 = cmath.exp(self.I * ((2.0 * pi * k) / n))
        return m2 * u2

    def ParametricPlot3D(self, builder):
        '''
        '''
        i = int(0)  # Sample count
        k = int(0)  # Dimension count
        maxA = float(1)
        maxB = float(pi / 2)
        stepB = maxB * self.Step

        for k1 in range(self.n):
            for k2 in range(self.n):
                for op in builder['before']:
                    op()

                for a in rs.frange(float(-1), maxA, self.Step):
                    for b in rs.frange(float(0), maxB, stepB):
                        if (a == -1 and k1 == 0 and k2 == 0):
                            k += 1

                        z1 = self.ComplexZ1(a, b, self.n, k1)
                        z2 = self.ComplexZ2(a, b, self.n, k2)

                        # Calculate point coords
                        x = self.Scale * (z1.real)
                        y = self.Scale * (z2.real)
                        z = self.Scale * ((
                            cos(self.Alpha) * z1.imag +
                            sin(self.Alpha) * z2.imag
                        ))

                        self.Points.append(Point3d(x, y, z))

                        for op in builder['build']:
                            op(a, b, i, k)

                        # Increment sample count
                        i += 1

                for op in builder['after']:
                    op()

def GenerateMatrix(inc=15):
    '''
    TODO Generate multiple manifolds and arrange in grid
    '''


def Run():
    n = rs.GetInteger('n', 1, 1)
    Alpha = rs.GetReal('Degree', 1.0, 0.0)
    Density = rs.GetReal('Density', 0.1, 0.01)
    Scale = rs.GetInteger('Scale', 100, 1)
    Type = rs.GetInteger('Type', 2, 1, 4)

    CalabiYau(n, Alpha, Density, Scale).Build(Type)


rs.EnableRedraw(True)

if __name__ == '__main__':
    Run()
