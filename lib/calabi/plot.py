'''
Replaces Grasshopper workflow -- execute via `RunPythonScript`

[](http://www.tanjiasi.com/surface-design/)
[](http://www.food4rhino.com/app/calabi-yau-manifold)
[Python Standard Library - math](https://docs.python.org/2/library/math.html)
[Python Standard Library - cmath](https://docs.python.org/2/library/cmath.html)

TOOD Assign elements to separate layers
'''

import importlib
import cmath
from math import cos, sin, pi
import rhinoscriptsyntax as rs
from scriptcontext import doc
from Rhino.Geometry import Point3d, Mesh, NurbsCurve, NurbsSurface, Curve, Brep, Vector3d, CurveKnotStyle
import System.Guid
import System.Enum
# from Rhino.Collections import Point3dList

# Import local modules
import export


class EventHandler:
    __slots__ = ['__registry__']

    def __init__(self):
        self.__registry__ = {}

    def register(self, subscribers):
        for event in subscribers.iterkeys():
            for func in subscribers[event]:
                self.subscribe(event, func)

        return self.__registry__

    def publish(self, event, *args, **kwargs):
        if event in self.__registry__:
            for func in self.__registry__[event]:
                func(*args, **kwargs)

    def subscribe(self, event, func):
        if not callable(func):
            raise TypeError(str(func) + 'is not callable')
        if event in self.__registry__ and type(self.__registry__) is list:
            self.__registry__[event].append(func)
        else:
            self.__registry__[event] = [func]


class Builder:
    def __init__(self, cy):
        self.CalabiYau = cy

    def Build(self, *args, **kwargs):
        return

    def Render(self, *args, **kwargs):
        return

    def __rendered__(self, obj):
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

    def Render(self, *args):
        for point in self.CalabiYau.Points:
            self.__rendered__(doc.Objects.AddPoint(point))
        doc.Views.Redraw()


class MeshBuilder(Builder):
    __slots__ = ['Mesh', 'SubMesh']

    def __init__(self, cy):
        Builder.__init__(self, cy)
        self.CalabiYau = cy
        self.Mesh = None
        self.SubMesh = None

    def __listeners__(self):
        return {
            'a.on': [self.BuildMesh],
            'b.on': [self.BuildSubMesh],
            'a.out': [self.JoinMesh]
        }

    def BuildMesh(self, *args):
        self.Mesh = Mesh()

    def BuildSubMesh(self, *args):
        k1, k2, a, b, i, k, point = args

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

    def JoinMesh(self, *args):
        self.Mesh.Weld(pi)
        self.CalabiYau.Meshes.append(self.Mesh)

    def Render(self, *args):
        for mesh in self.CalabiYau.Meshes:
            self.__rendered__(doc.Objects.AddMesh(mesh))

        doc.Views.Redraw()

    def AppendVertex(self, i):
        '''
        Parameters:
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
    __slots__ = []

    '''
    Refer to [Curves Experimentation](https://bitbucket.org/snippets/kunst_dev/X894E8)
    '''
    def __init__(self, cy):
        Builder.__init__(self, cy)
        self.CalabiYau = cy
        self.C1 = None  # bound_start
        self.C2 = None  # bound_end
        self.C3 = None  # curve_outer
        self.C4 = None  # curve_inner
        self.SubCurves = None
        self.SubPoints = None
        self.Curves = []
        self.Breps = []
        self.U = []
        self.V = []

    def __listeners__(self):
        return {
            'k1.on': [self.Before],
            'a.in': [self.Build]
        }

    def Before(self, *args):
        self.C1 = []
        self.C2 = []
        self.C3 = []
        self.C4 = []
        self.SubCurves = []
        self.SubPoints = []
        # self.V.append([])
        self.U.append([])

    def Build(self, *args):
        '''
        TODO Ensure domain corner anchored to centre point
        TOOD Group points by surface domain
        TODO Group quad surface curves
        TODO Fit surface to domain points
        '''
        a, b, i, k, point = args

        self.SubPoints.append(point)

        u = self.U[-1]
        # self.V[-1]

        if a == self.CalabiYau.RngA[0]:
            self.C4.append(point)
            # u.append(point)
            # v.append(point)
        elif a == self.CalabiYau.RngA[-1]:
            self.C3.append(point)
            # u.append(point)
            # v.append(point)
        elif b == self.CalabiYau.RngB[0]:  # is this necessary?
            self.C1.append(point)
        elif b == self.CalabiYau.RngB[-1]:
            self.C2.append(point)

        # TODO do we need to be adding this to the front of the array arr.insert(0, val)
        if a == self.CalabiYau.RngA[0] or a == self.CalabiYau.RngA[-1]:
            u.append(point)
            # v.append(point)
            if b == self.CalabiYau.RngB[0]:
                self.C1.append(point)
            elif b == self.CalabiYau.RngB[-1]:
                self.C2.append(point)

    # Panelling tools?
    # NetworkSrf - Surface from curves
    # rs.AddSrfControlPtGrid
    # NurbsSurface.CreateNetworkSurface
    # Rhino.AddNetworkSrf (arrCurves [, intContinuity [, dblEdgeTolerance [, dblInteriorTolerance [, dblAngleTolerance]]]])
    # rs.AddSrfPtGrid
    # u, v = len(self.CalabiYau.RngB), len(self.CalabiYau.RngB)
    # points = rs.coerce3dpointlist(self.SubPoints, True)
    # surf = NurbsSurface.CreateThroughPoints(points, u, v, 3, 3, False, False)
    # rs.AddSrfPtGrid([u, v], self.SubPoints)
    def After(self, *args):
        print len(self.U[-1])
        # print len(self.V[-1])

        for curve in self.CreateInterpolatedCurves(*self.U):
            self.__rendered__(doc.Objects.AddCurve(curve))
            if rs.GetBoolean('Proceed',  ('Proceed?', 'No', 'Yes'), (True)) is None:
                break

        # self.CreateInterpolatedCurves()
        # for curve in self.CreateInterpolatedCurves(self.C1, self.C2, self.C3, self.C4):
        #     self.SubCurves.append(curve)
        #
        # self.Curves.append(self.SubCurves)

        # self.Breps.append(self.CreateBrep())

    def Render(self, *args):
        # print len(self.Breps)

        # for point in self.CalabiYau.Points:
        #     self.__rendered__(doc.Objects.AddPoint(point))
        #
        # for curveGroup in self.Curves:
        #     for curve in curveGroup:
        #         self.__rendered__(doc.Objects.AddCurve(curve))
        #
        # for brep in self.Breps:
        #     try:
        #         self.__rendered__(doc.Objects.AddBrep(brep))
        #     except Exception:
        #         continue

        doc.Views.Redraw()

    def CreateInterpolatedCurve(self, points):
        '''
        TODO rescue Exception raised if insufficient points

        [](http://developer.rhino3d.com/samples/rhinocommon/surface-from-edge-curves/)
        `rs.AddInterpCurve`
        '''
        points = rs.coerce3dpointlist(points, True)

        start_tangent = Vector3d.Unset
        start_tangent = rs.coerce3dvector(start_tangent, True)

        end_tangent = Vector3d.Unset
        end_tangent = rs.coerce3dvector(end_tangent, True)

        knotstyle = System.Enum.ToObject(CurveKnotStyle, 0)

        curve = Curve.CreateInterpolatedCurve(points, 3, knotstyle, start_tangent, end_tangent)

        if curve:
            return curve
        raise Exception('Unable to CreateInterpolatedCurve')

    def CreateInterpolatedCurves(self, *args):
        '''
        '''
        return map(self.CreateInterpolatedCurve, args)

    def CreateBrep(self):
        '''
        Boundary Representation (Brep) from 4 curves

        TODO RssLib/rhinoscript/surface.py
            rs.AddSrfContourCrvs
            rs.AddSrfControlPtGrid
            rs.AddSrfPt
            rs.AddSrfPtGrid
        '''

        return Brep.CreateEdgeSurface(self.SubCurves)


class CalabiYau:
    '''
    Attributes:
        n : int
            [1..10]
            Dimensions of Calabi Yau Manifold
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
        Builder : class
    '''

    __slots__ = ['n', 'Alpha', 'Step', 'Scale', 'MaxA', 'MaxB', 'StepB',
                 'RngK', 'RngA', 'RngB', 'Points']

    __builder__ = {
        1: PointCloudBuilder,
        2: MeshBuilder,
        3: CurveBuilder,
        4: SurfaceBuilder
    }

    # TODO move static equation functions into module
    I = complex(0.0, 1.0)

    @staticmethod
    def U1(a, b):
        m1 = cmath.exp(complex(a, b))
        m2 = cmath.exp(complex(-a, -b))
        return (m1 + m2) * 0.5

    @staticmethod
    def U2(a, b):
        m1 = cmath.exp(complex(a, b))
        m2 = cmath.exp(complex(-a, -b))
        return (m1 - m2) * 0.5

    @staticmethod
    def Z1(a, b, n, k):
        u1 = CalabiYau.U1(a, b) ** (2.0 / n)
        m1 = cmath.exp(CalabiYau.I * ((2.0 * pi * k) / n))
        return m1 * u1

    @staticmethod
    def Z2(a, b, n, k):
        u2 = CalabiYau.U2(a, b) ** (2.0 / n)
        m2 = cmath.exp(CalabiYau.I * ((2.0 * pi * k) / n))
        return m2 * u2

    @staticmethod
    def calc(n, alpha, k1, k2, a, b):
        '''
        Returns:
            R3 coordinates (x, y, z) as complex

        Parameters:
            n : int
            alpha : float
            k1 : float
            k2 : float
            a : float
            b : float
        '''
        z1 = CalabiYau.Z1(a, b, n, k1)
        z2 = CalabiYau.Z2(a, b, n, k2)

        return (z1.real), (z2.real), (cos(alpha) * z1.imag + sin(alpha) * z2.imag)

    def __init__(self, n=1, deg=1.0, step=0.1, scale=1, builder=4):
        '''
        Parameters:
            builder : int
                [1] generate Rhino.Geometry.Point
                [2] generate Rhino.Geometry.Mesh
                [3] generate Rhino.Geometry.Curve
                [4] generate Rhino.Geometry.Surface
        '''
        self.n = n
        self.Alpha = deg * pi
        self.Step = step
        self.Scale = scale
        self.MaxA = float(1)
        self.MaxB = float(pi / 2)
        self.StepB = self.MaxB * self.Step
        self.RngK = range(self.n)
        self.RngA = rs.frange(float(-1), self.MaxA, self.Step)
        self.RngB = rs.frange(float(0), self.MaxB, self.StepB)

        self.Points = []
        self.Domains = []
        self.Meshes = []
        self.Builder = CalabiYau.__builder__[builder]

        # Setup Events registry
        self.Events = EventHandler()
        for d in ['k1', 'k2', 'a', 'b']:
            for event in ['on', 'in', 'out']:
                self.Events.__registry__['.'.join(d + event)] = []

    def Build(self):
        builder = self.Builder(self)
        # Register listeners if defined
        if hasattr(self.Builder, '__listeners__') and callable(self.Builder.__listeners__):
            builder.self.Events.register(builder.__listeners__())
        self.ParametricPlot3D()
        builder.Render()

    def Point(self, *args):
        '''
        Calculate point coords
        TODO Confirm; are we always moving right to left?
        '''
        return Point3d(*map(
            lambda x: x * self.Scale,
            CalabiYau.calc(self.n, self.Alpha, *args)))

    def ParametricPlot3D(self):
        '''
        Registered 'on', 'in', 'out' callbacks will be executed in turn per nested loop.

        Examples:
        ```
            # Calculate iterations
            self.n * self.n * len(self.RngA) * len(self.RngB)
        ````
        '''

        i = int(0)  # Cumulative position within nested loop -- equiv to `len(self.Points)`
        k = int(0)  # Dimension count

        for k1 in self.RngK:
            self.Events.publish('k1.on', k1, i, k)
            self.Events.publish('k1.in', k1, i, k)

            # Break out first iteration
            # if k1 == self.RngK[1]: break

            for k2 in self.RngK:
                self.Events.publish('k2.on', k1, k2, i, k)
                self.Events.publish('k2.in', k1, k2, i, k)

                # Break out first iteration
                # if k2 == self.RngK[1]: break

                for a in self.RngA:
                    self.Events.publish('a.on', k1, k2, a, i, k)
                    self.Events.publish('a.in', k1, k2, a, i, k)

                    for b in self.RngB:
                        if (a == -1 and k1 == 0 and k2 == 0): k += 1

                        self.Events.publish('b.on', k1, k2, a, b, i, k)

                        point = self.Point(k1, k2, a, b)
                        self.Points.append(point)

                        self.Events.publish('b.in', k1, k2, a, b, i, k, point)
                        self.Events.publish('b.out', k1, k2, a, b, i, k)

                        # Increment loop position
                        i += 1

                    self.Events.publish('a.out', k1, k2, a, i, k)

                self.Events.publish('k2.out', k1, k2, i, k)

            self.Events.publish('k1.out', k1, i, k)


def Halt():
    '''
    In lieu of MacOS debugger this will have to do.
    '''
    if rs.GetBoolean('Proceed',  ('Proceed?', 'No', 'Yes'), (True)) is None:
        return None

def GenerateMatrix(inc=15):
    '''
    TODO Generate multiple manifolds and arrange in grid
    '''


def Run():
    n = rs.GetInteger('n', 2, 1, 10)
    Alpha = rs.GetReal('Degree', 1.0, 0.0, 1.0)
    Density = rs.GetReal('Density', 0.1, 0.01, 0.2)
    Scale = rs.GetInteger('Scale', 100, 1, 100)
    Builder = rs.GetInteger('Type', 1, 1, 4)

    CalabiYau(n, Alpha, Density, Scale, Builder).Build()


rs.EnableRedraw(True)

if __name__ == '__main__':
    Run()
