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
from scriptcontext import doc
from Rhino.Geometry import Point3d, Mesh, NurbsCurve, Curve, Brep, Vector3d, CurveKnotStyle
import System.Guid
import System.Enum
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

    def __rendered__(obj):
        '''
        Confirm `obj` has Guid
        '''
        if obj == System.Guid.Empty:
            raise Exception('RenderError')

        return True


class PointCloudBuilder(Builder):
    def __init__(self, cy):
        Builder.__init__(self, cy)
        self.CalabiYau = cy

    def Render(self):
        for point in self.CalabiYau.Points:
            self.__rendered__(doc.Objects.AddPoint(point))
        doc.Views.Redraw()


class MeshBuilder(Builder):
    def __init__(self, cy):
        Builder.__init__(self, cy)
        self.CalabiYau = cy
        self.Mesh = None
        self.SubMesh = None

    def Before(self):
        self.Mesh = Mesh()

    def Build(self, *args):
        a, b, i, k, point = args












        # MAYBE THIS WILL REMOVE THOSE ADDITIONAL SURFACES








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
            self.__rendered__(doc.Objects.AddMesh(mesh))

        doc.Views.Redraw()

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


class CurveBuilder(Builder):
    def __init__(self, cy):
        Builder.__init__(self, cy)
        self.CalabiYau = cy


# TODO Move Curve behaviour into CurveBuilder and inherit
class SurfaceBuilder(Builder):
    def __init__(self, cy):
        Builder.__init__(self, cy)
        self.CalabiYau = cy
        self.C1 = None  # bound_start
        self.C2 = None  # bound_end
        self.C3 = None  # curve_outer
        self.C4 = None  # curve_inner
        self.SubCurves = None
        self.Curves = []
        self.Breps = []

    def Before(self):
        self.C1 = []
        self.C2 = []
        self.C3 = []
        self.C4 = []
        self.SubCurves = []

    def Build(self, *args):
        a, b, i, k, point = args

        if a == self.CalabiYau.RngA[0]:
            self.C4.append(point)
        elif a == self.CalabiYau.RngA[-1]:
            self.C3.append(point)
        elif b == self.CalabiYau.RngB[0]:
            self.C1.append(point)
        elif b == self.CalabiYau.RngB[-1]:
            self.C2.append(point)

        if a == self.CalabiYau.RngA[0] or a == self.CalabiYau.RngA[-1]:
            if b == self.CalabiYau.RngB[0]:
                self.C1.append(point)
            elif b == self.CalabiYau.RngB[-1]:
                self.C2.append(point)

    def After(self):
        self.CreateInterpolatedCurves()
        self.Breps.append(self.CreateBrep())

    def Render(self):
        print len(self.Breps)

        # for brep in self.Breps:
        #     __rendered__(doc.Objects.AddBrep(brep))

        for curve in self.Curves:
            self.__rendered__(doc.Objects.AddCurve(curve))

        doc.Views.Redraw()

    def CreateInterpolatedCurves(self):
        '''
        TODO group quad surface curves
        TODO rescue Exception raised if insufficient points

        [](http://developer.rhino3d.com/samples/rhinocommon/surface-from-edge-curves/)
        `rs.AddInterpCurve`
        '''
        for points in self.C1, self.C2, self.C3, self.C4:
            points = rs.coerce3dpointlist(points, True)

            start_tangent = Vector3d.Unset
            start_tangent = rs.coerce3dvector(start_tangent, True)

            end_tangent = Vector3d.Unset
            end_tangent = rs.coerce3dvector(end_tangent, True)

            knotstyle = System.Enum.ToObject(CurveKnotStyle, 0)

            crv = Curve.CreateInterpolatedCurve(points, 3, knotstyle, start_tangent, end_tangent)

            if not crv:
                raise Exception("Unable to CreateInterpolatedCurve")
            else:
                self.SubCurves.append(crv)

        return self.SubCurves

    def CreateBrep(self):
        '''
        Boundary Representation (Brep) from 4 curves
        '''
        return Brep.CreateEdgeSurface(self.SubCurves)


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
            3: self.CurveBuilder,
            4: self.SurfaceBuilder
        }
        self.MaxA = float(1)
        self.MaxB = float(pi / 2)
        self.StepB = self.MaxB * self.Step
        self.RngK = range(self.n)
        self.RngA = rs.frange(float(-1), self.MaxA, self.Step)
        self.RngB = rs.frange(float(0), self.MaxB, self.StepB)

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
        Refer to [Curves Experimentation](https://bitbucket.org/snippets/kunst_dev/X894E8)

        Calculate iterations `self.n * self.n * len(self.RngA) * len(self.RngB)`
        '''

        i = int(0)  # Cumulative position within nested loop -- equiv to `len(self.Points)`
        k = int(0)  # Dimension count

        for k1 in self.RngK:
            # Break after first iteration
            # if k1 == self.RngK[1]: break

            for k2 in self.RngK:
                # if k2 == self.RngK[1]: break

                for op in builder['before']:
                    op()

                for a in self.RngA:
                    for b in self.RngB:
                        if (a == -1 and k1 == 0 and k2 == 0): k += 1

                        z1 = self.ComplexZ1(a, b, self.n, k1)
                        z2 = self.ComplexZ2(a, b, self.n, k2)

                        # Calculate point coords
                        x = self.Scale * (z1.real)
                        y = self.Scale * (z2.real)
                        z = self.Scale * ((
                            cos(self.Alpha) * z1.imag +
                            sin(self.Alpha) * z2.imag
                        ))

                        # TODO Confirm; are we always moving right to left?
                        point = Point3d(x, y, z)
                        self.Points.append(point)

                        for op in builder['build']:
                            op(a, b, i, k, point)

                        # Increment loop position
                        i += 1

                for op in builder['after']:
                    op()


def Halt():
    '''
    In lieu of MacOS debugger this will have to do.
    '''
    if rs.GetBoolean('Proceed',  ('Proceed?', 'No', 'Yes'), (True)) is None:
        return


def GenerateMatrix(inc=15):
    '''
    TODO Generate multiple manifolds and arrange in grid
    '''


def Run():
    n = rs.GetInteger('n', 2, 1, 10)
    Alpha = rs.GetReal('Degree', 1.0, 0.0, 1.0)
    Density = rs.GetReal('Density', 0.1, 0.01, 0.2)
    Scale = rs.GetInteger('Scale', 100, 1, 100)
    Type = rs.GetInteger('Type', 4, 1, 4)

    CalabiYau(n, Alpha, Density, Scale).Build(Type)


rs.EnableRedraw(True)

if __name__ == '__main__':
    Run()
