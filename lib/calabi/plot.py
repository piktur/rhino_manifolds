'''
Replaces Grasshopper workflow -- execute via `RunPythonScript`

[](http://www.tanjiasi.com/surface-design/)
[](http://www.grasshopper3d.com/video/calabi-yau-manifold-in-grasshopper)
'''

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


class Builder:
    def __init__(self, cy):
        self.CalabiYau = cy

    def Before(self):
        '''
        '''
        return

    def Build(self):
        '''
        '''
        return

    def After(self):
        '''
        '''
        return

    def Render(self):
        '''
        '''
        return


class PointCloudBuilder(Builder):
    def __init__(self, cy):
        Builder.__init__(self, cy)
        self.CalabiYau = cy

    def Render(self):
        for point in self.CalabiYau.Points:
            rs.AddPoint(point)


class SurfaceBuilder(Builder):
    def __init__(self, cy):
        Builder.__init__(self, cy)
        self.CalabiYau = cy


class MeshBuilder(Builder):
    def __init__(self, cy):
        Builder.__init__(self, cy)
        self.CalabiYau = cy
        self.Mesh = None
        self.SubMesh = None

    def Before(self):
        self.Mesh = Mesh()

    def Build(self, *args):
        i, k = args
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
        mesh : Rhino.Geometry.Mesh
        '''
        try:
            p = self.CalabiYau.Points[i]
            self.SubMesh.Vertices.Add(p.X, p.Y, p.Z)
        except IndexError:
            print 'Points[' + str(i) + '] out of range'
            return


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
    Step : float
        [0.01..0.1]
        Sample rate
    Scale : int
        [1..100]
    Points : list<Rhino.Geometry.Point3d>
    Meshes : list<Rhino.Geometry.Mesh>
    '''
    def __init__(self, n=1, deg=1.0, step=0.1, scale=1):
        self.n = n
        self.I = complex(0.0, 1.0)
        self.Alpha = deg
        self.Step = step
        self.Scale = scale
        self.Points = []
        self.Meshes = []
        self.Builder = {
            1: self.PointCloudBuilder,
            2: self.MeshBuilder,
            3: self.SurfaceBuilder,
        }

    def __ops__(self, builder):
        return {
            1: [builder.Before],
            2: [builder.Build],
            3: [builder.After],
            4: builder.Render
        }

    def PointCloudBuilder(self):
        return self.__ops__(PointCloudBuilder(self))

    def MeshBuilder(self):
        return self.__ops__(MeshBuilder(self))

    def SurfaceBuilder(self):
        return self.__ops__(SurfaceBuilder(self))

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
        builder[4]()

    def ComplexU1(self, a, b):
        m1 = cmath.exp(complex(a, b))
        m2 = cmath.exp(complex(-a, -b))
        return (m1 + m2) * 0.5

    def ComplexU2(self, a, b):
        m1 = cmath.exp(complex(a, b))
        m2 = cmath.exp(complex(-a, -b))
        return (m1 - m2) * 0.5

    def ComplexZ1(self, a, b, n, k):
        u1 = self.ComplexU1(a, b) ** complex(2.0 / n)
        m1 = cmath.exp(self.I * complex((2.0 * pi * k) / n))
        return m1 * u1

    def ComplexZ2(self, a, b, n, k):
        u2 = self.ComplexU2(a, b) ** complex(2.0 / n)
        m2 = cmath.exp(self.I * complex((2.0 * pi * k) / n))
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
                # Call Setup functions
                for cb in builder[1]:
                    cb()

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

                        if a > -1:
                            if b > 0:
                                # Call each
                                for cb in builder[2]:
                                    cb(i, k)

                        # Increment sample count
                        i += 1

                # Call finalize functions
                for cb in builder[3]:
                    cb()


def Run(type=2):
    n = rs.GetInteger('n', 1, 1)
    Alpha = rs.GetReal('Degree', 1.0, 0.0)
    Density = rs.GetReal('Density', 0.1, 0.01)
    Scale = rs.GetInteger('Scale', 100, 1)

    CalabiYau(n, Alpha, Density, Scale).Build(type)


rs.EnableRedraw(True)

if __name__ == '__main__':
    Run()
