import os
import cmath
from math import cos, sin, pi, fabs
from itertools import combinations
import System.Guid
import System.Drawing
import System.Enum
from System.Drawing import Color
from scriptcontext import doc, sticky
# from rhinoscriptsyntax import GetBoolean, GetInteger,
#   GetReal, AddObjectsToGroup, AddGroup, frange
import rhinoscriptsyntax as rs
from Rhino.Geometry import Brep, ControlPoint, Curve, CurveKnotStyle, Mesh, NurbsCurve, NurbsSurface, Point3d, Vector3d, Intersect
from Rhino.Collections import Point3dList, CurveList
import utility
import export
from export import fname
import layers
from events import EventHandler


reload(utility)
reload(export)
reload(layers)


def GetUserInput():
    n = rs.GetInteger('n', 5, 1, 10)
    alpha = rs.GetReal('Degree', 0.25, 0.0, 2.0)
    density = rs.GetReal('Density', 0.1, 0.01, 0.4)
    scale = rs.GetInteger('Scale', 100, 1, 100)
    offset = rs.GetInteger('Offset', 0, -10, 10) * 300
    offset = (offset, offset)
    builder = rs.GetInteger('Type', 4, 1, 5)

    return n, alpha, density, scale, offset, builder


def GenerateGrid(density=0.1, scale=100, type=4):
    '''
    Generate 10 x 10 grid
    '''
    arr = []
    offset = scale * 3
    originY = 0
    originX = 0
    x = originX
    y = originY
    alpha = rs.frange(0.1, 1.0, 0.1)

    for n in rs.frange(1, 10, 1):
        x = originX + (n * offset)
        y = originY

        for a in alpha:
            arr.append(Builder(int(n), a, density, scale, (x, y), type))
            y += offset

        originY = 0
        originX += offset

    for obj in arr:
        obj.Build()
        doc.Views.Redraw()


def Batch(dir, density=0.1, scale=100, type=4):
    queue = {}
    offset = scale * 3
    alpha = 0.25  # rs.frange(0.1, 1.0, 0.1)

    for n in rs.frange(2, 9, 1):
        # for a in alpha:
        #     out = export.fname('3dm', os.path.join(dir, str(n)), 'CY', str(int(a * 10)))
        #     queue[out] = Builder(int(n), a, density, scale, (0, 0), type)
        out = export.fname('3dm', os.path.join(dir, str(n)), 'CY', n, str(float(alpha)))
        queue[out] = Builder(int(n), alpha, density, scale, (0, 0), type)

    return queue


def Run(*args):
    if rs.ContextIsRhino():  # rs.ContextIsGrasshopper()
        args = GetUserInput()

    # Cache builder instance
    sticky['builder'] = Builder(*args)
    sticky['builder'].Build()

    doc.Views.Redraw()


def Layers():
    layers.Build()
    doc.Views.Redraw()


PointAnalysis = {'Seq': {}}
I = complex(0.0, 1.0)


def U1(xi, theta):
    '''
    Complex extensions of the sine and cosine
    [Equation (4)](https://www.cs.indiana.edu/~hansona/papers/CP2-94.pdf)
    See (plot_6.nb)[/examples/mathematica/plot_6.nb]
    '''
    # return (0.5 * I) * (cmath.exp(xi + (I * theta)) + cmath.exp(-xi - (I * theta)))
    return 0.5 * (cmath.exp(complex(xi, theta)) + cmath.exp(complex(-xi, -theta)))


def U2(xi, theta):
    # return (-0.5 * I) * (cmath.exp(xi + (I * theta)) - cmath.exp(-xi - (I * theta)))
    return 0.5 * (cmath.exp(complex(xi, theta)) - cmath.exp(complex(-xi, -theta)))


def phase(n, k):
    '''
    Phase factor is the `n`th root of unity for integers 0 < k < (n - 1)
    [Equation (7)](https://www.cs.indiana.edu/~hansona/papers/CP2-94.pdf)
    [`CalabiYau.RngK`](/lib/calabi_yau/manifold.py)
    '''
    return cmath.exp(k * 2 * pi * I / n)


def Z0(z1, z2, n):
    '''
    [Equation (3)](https://www.cs.indiana.edu/~hansona/papers/CP2-94.pdf)
    '''
    return (z1 ** n) + (z2 ** n)


def Z1(xi, theta, n, k):
    '''
    [Equation (5)](https://www.cs.indiana.edu/~hansona/papers/CP2-94.pdf)
    '''
    u1 = U1(xi, theta) ** (2.0 / n)
    return phase(n, k) * u1


def Z2(xi, theta, n, k):
    '''
    [Equation (6)](https://www.cs.indiana.edu/~hansona/papers/CP2-94.pdf)
    '''
    u2 = U2(xi, theta) ** (2.0 / n)
    return phase(n, k) * u2


def PZ1(xi, theta, n, k):
    '''
    [Hanson, Table 1](https://www.cs.indiana.edu/~hansona/papers/CP2-94.pdf)
    "Power surface: Replace zi --> pzi and Pi/2 --> 2 Pi" What?
    Is this the polynomial example as in [Figure 7]
    '''
    # phase(n, k) * cmath.exp((xi + I * theta) / n)
    return phase(n, k) * cmath.exp(complex(xi, theta) / n)


def PZ2(xi, theta, n, k):
    return phase(n, -k) * cmath.exp(complex(-xi, -theta) / n)


def Genus(n):
    '''
    [Equation (8)](https://www.cs.indiana.edu/~hansona/papers/CP2-94.pdf)
    '''
    return (n - 1) * (n - 2) / 2


def EulerCharacteristic(n):  # Denoted by the Greek lower-case character 'chi'
    '''
    [Equation (9)](https://www.cs.indiana.edu/~hansona/papers/CP2-94.pdf)
    '''
    return 2 - (2 * Genus(n))  # (3 * n) - (n ** 2)


def CalculatePoint(n, angle, k1, k2, xi, theta):
    '''
    The surface is composed of n ** 2 patches, each parameterized in a
    rectangular complex domain. The rectangular patches are pieced together
    about a point in groups of n * 2. The surface has `n` seperate boundary
    edges.

    The structure and complexity of the surface is characterised by the
    exponent `n`. In Hanson's parameterization, the surface is computed in a
    space defined by two real and two imaginary axes The real axes are remapped
    to **x** and **y**, while the imaginary axes are projected into the depth
    dimension **z** after rotation by `angle`
    [Stewart Dickson](https://muse.jhu.edu/article/43586)

    Returns:
        R3 coordinates (x, y, z)

    Parameters:
        n : int
        angle : float
        k1 : float
        k2 : float
        a : float
        b : float
    '''
    _ = PointAnalysis
    _['z1'] = z1 = Z1(xi, theta, n, k1)
    _['z2'] = z2 = Z2(xi, theta, n, k2)
    _['z0'] = z0 = Z0(z1, z2, n)

    # Polynomial form
    # _['pz1'] = pz1 = PZ1(xi, theta, n, k1)
    # _['pz2'] = pz2 = PZ2(xi, theta, n, k2)

    _['x'] = x = z1.real
    _['y'] = y = z2.real
    _['z'] = z = cos(angle) * z1.imag + sin(angle) * z2.imag

    return x, y, z


class Patch:
    '''
    Attributes:
        Points : Rhino.Collections.Point3dList
        Surface : Rhino.Geometry.NurbsSurface
        Surfaces : list<Rhino.Geometry.NurbsSurface>
        Brep : Rhino.Geometry.Brep
        MeshA : Rhino.Geometry.Mesh
        MeshB : Rhino.Geometry.Mesh
        Edges : list<Rhino.Geometry.NurbsCurve>
    '''
    __slots__ = [
        'CalabiYau',
        'Phase'
        'Analysis',
        'Points',
        'Surface', 'Surfaces',
        'Brep',
        'MeshA', 'MeshB',
        'Edges'
    ]

    def __init__(self, cy, phase):
        self.CalabiYau = cy
        self.Phase = phase
        self.Analysis = {}
        self.Points = Point3dList()
        self.Surfaces = []
        # self.Edges = []
        # self.Brep = None


class Builder:
    '''
    Algorithm based on [Andrew J. Hanson](https://www.cs.indiana.edu/~hansona/papers/CP2-94.pdf).

    See:
        * [Python Standard Library - math](https://docs.python.org/2/library/math.html)
        * [Python Standard Library - cmath](https://docs.python.org/2/library/cmath.html)
        * [](http://www.tanjiasi.com/surface-design/)
        * [](http://www.food4rhino.com/app/calabi-yau-manifold)

    Following Hanson's conventions for symbolic representation:
        * `U == a == xi`
        * `V == b == theta`

    Subdivisions ensure geometry comes together at `Patch.Analysis['centre']`

    Parameters:
        n : int
        deg : float
        step : float
        scale : int
        offset : int
        type : int

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
        Offset : tuple(int, int)
        Phases : list
        MaxU : float
        MaxV : float
        StepV : float
        RngK : range
        RngU : range
        RngV : range
        __builder__ : class
        __palette__ : list<list<System.Drawing.Color>>
        Analysis: dict
        Points : list<Rhino.Geometry.Point3d>
        Point : Rhino.Geometry.Point3d
        PointCount : int
            Cumulative position within `Plot3D` nested loop --
            equiv to `len(self.Points)`
        Patches : list<Patch>
        Patch : Patch
        PatchCount : int
    '''
    __slots__ = ['n', 'Alpha', 'Step', 'Scale', 'Offset',
                 'U', 'V',
                 'UDegree', 'VDegree',
                 'MinU', 'MaxU', 'StepU', 'CentreU',
                 'MinV', 'MaxV', 'StepV', 'CentreV',
                 'RngK', 'RngU', 'RngV',
                 'Analysis',
                 'Points', 'Point', 'PointCount',
                 'Patches', 'Patch', 'PatchCount',
                 '__builder__',
                 '__palette__']

    def __init__(self, n=1, deg=1.0, step=0.1, scale=1, offset=(0, 0), type=4):
        '''
        Parameters:
            type : int
                [1] generate Rhino.Geometry.Point
                [2] generate Rhino.Geometry.Mesh
                [3] generate Rhino.Geometry.Curve
                [4] generate Rhino.Geometry.Surface
        '''
        self.n = n
        self.Alpha = deg * pi
        self.Step = step
        self.Scale = scale
        self.Offset = offset

        # Floating point precision.
        # Increase when self.U and/or self.V increases
        self.ndigits = 5

        # NOTE `U` -- "xi" must be odd to guarantee passage through fixed points at
        # (theta, xi) = (0, 0) and (theta, xi) = (pi / 2, 0)
        # [Table 1](https://www.cs.indiana.edu/~hansona/papers/CP2-94.pdf)
        # Performance reduced if > 55
        self.V = self.U = 55  # 11, 21, 55, 107, 205 [110]

        self.VDegree = self.UDegree = 3

        self.MinU = -1
        self.MaxU = 1
        # deduct 1 to accomodate `rs.frange` zero offset
        self.StepU = fabs(self.MaxU - self.MinU) / (self.U - 1.0)

        self.MinV = 0
        self.MaxV = float(pi / 2)
        # deduct 1 to accomodate `rs.frange` zero offset
        self.StepV = fabs(self.MaxV - self.MinV) / (self.V - 1.0)

        self.RngK = rs.frange(0, n - 1, 1)  # range(self.n)
        self.RngU = rs.frange(self.MinU, self.MaxU, self.StepU)
        self.RngV = rs.frange(self.MinV, self.MaxV, self.StepV)

        self.CentreU = len(self.RngU) / 2
        self.CentreV = len(self.RngV) / 2

        self.Points = []
        self.Point = None
        self.PointCount = 0

        self.Patches = []
        self.Patch = None
        self.PatchCount = 0
        self.__palette__ = utility.Palette()

        self.Analysis = PointAnalysis
        self.Analysis['g'] = Genus(self.n)
        self.Analysis['chi'] = EulerCharacteristic(self.n)

        if type == 5:
            # TODO
            # self.__builder__ = __builders__
            pass
        elif type is None:
            raise Exception('Builder not specified')
        else:
            self.__builder__ = __builders__[type]

        # Setup Events registry
        self.Events = EventHandler()
        for loop in ['k1', 'k2', 'a', 'b']:
            for event in ['on', 'in', 'out']:
                self.Events.__registry__['.'.join([loop, event])] = []

    def __listeners__(self):
        return {
            'k1.on': [],
            'k1.in': [],
            'k2.on': [self.AddPatch],
            'k2.in': [],
            'a.on': [],
            'a.in': [],
            'b.on': [self.BuildPoint],
            'b.in': [],
            'b.out': [],
            'a.out': [],
            'k2.out': [],
            'k1.out': []
        }

    def Build(self):
        '''
        Register `self.__builder__.__listeners__`

        Iterates `self.n ** 2` "phases" plotting the topology of the
        "Fermat surface" of degree `n`.
        There are `self.n ** 2` `Patch`es per surface.

        `self.__builder__` functions registered with 'on', 'in', 'out' events will be
        called in order once per nested loop.

        Add Rhino objects to document
        '''
        builder = self.__builder__(self.n, self.Alpha / pi, self.Step, self.Scale, self.Offset)

        if hasattr(self.__builder__, '__listeners__') and callable(self.__builder__.__listeners__):
            self.Events.register(builder.__listeners__())

        for k1 in self.RngK:
            self.Events.publish('k1.on', k1)
            self.Events.publish('k1.in', k1)

            for k2 in self.RngK:
                self.Events.publish('k2.on', k1, k2)
                self.Events.publish('k2.in', k1, k2)

                for a in self.RngU:
                    self.Events.publish('a.on', k1, k2, a)
                    self.Events.publish('a.in', k1, k2, a)

                    for b in self.RngV:
                        self.Events.publish('b.on', k1, k2, a, b)
                        self.Events.publish('b.in', k1, k2, a, b)
                        self.Events.publish('b.out', k1, k2, a, b)

                    self.Events.publish('a.out', k1, k2, a)

                self.Events.publish('k2.out', k1, k2)

            self.Events.publish('k1.out', k1)

        builder.Render(self)

    def PointAnalysis(self, *args):
        '''
        [Figure 4](https://www.cs.indiana.edu/~hansona/papers/CP2-94.pdf)
        Store 3d point coordinates at significant angles/U count
        '''
        k1, k2, xi, theta = args
        _ = self.Analysis
        d = self.ndigits

        # Patch predicates
        # [Figure 4](https://www.cs.indiana.edu/~hansona/papers/CP2-94.pdf)
        _['z0 == 0'] = round(_['z0'].imag, d) == 0
        _['z0 == 1'] = round(_['z0'].imag, d) == 1
        _['z0 == -1'] = round(_['z0'].imag, d) == -1
        _['z1 == 0'] = round(_['z1'].imag, d) == 0
        _['z2 == 0'] = round(_['z2'].imag, d) == 0

        _['minU'] = round(xi, 1) == self.MinU  # -1
        _['midU'] = round(xi, 1) == (self.MinU + self.MaxU)  # 0
        _['maxU'] = round(xi, 1) == self.MaxU  # 1

        # Intervals through RngV
        # `range(0, 90, 15)`
        _['theta == 0'] = round(theta, d) == float(0)  # self.MinV
        _['theta == 15'] = round(theta, d) == round(pi / 12, d)
        _['theta == 30'] = round(theta, d) == round(pi / 6, d)
        _['theta == 45'] = round(theta, d) == round(pi / 4, d)
        _['theta == 60'] = round(theta, d) == round(pi / 3, d)
        _['theta == 75'] = round(theta, d) == round(pi / 2.4, d)
        _['theta == 90'] = round(theta, d) == round(pi / 2, d)  # self.MaxV

        # The junction of n patches is a fixed point of a complex phase transformation.
        # The n curves converging at this fixed point emphasize the dimension of the surface.
        # Point of convergence "hyperbolic pie chart"
        _['min0'] = _['theta == 0'] and _['minU']
        # _['mid0'] = _['z1 == 0'] or _['z2 == 0'] and _['midU']
        _['centre'] = _['mid0'] = _['theta == 0'] and _['midU']
        _['max0'] = _['theta == 0'] and _['maxU']

        _['min45'] = _['theta == 45'] and _['minU']
        _['mid45'] = _['theta == 45'] and _['midU']
        _['max45'] = _['theta == 45'] and _['maxU']

        _['min90'] = _['theta == 90'] and _['minU']
        _['mid90'] = _['theta == 90'] and _['midU']
        _['max90'] = _['theta == 90'] and _['maxU']

        if _['min0'] is True:
            self.Patch.Analysis['min0'] = self.Point
        elif _['mid0'] is True:
            self.Patch.Analysis['centre'] = self.Patch.Analysis['mid0'] = self.Point
        elif _['max0'] is True:
            self.Patch.Analysis['max0'] = self.Point

        elif _['min45'] is True:
            self.Patch.Analysis['min45'] = self.Point
        elif _['mid45'] is True:
            self.Patch.Analysis['mid45'] = self.Point
        elif _['max45'] is True:
            self.Patch.Analysis['max45'] = self.Point

        elif _['min90'] is True:
            self.Patch.Analysis['min90'] = self.Point
        elif _['mid90'] is True:
            self.Patch.Analysis['mid90'] = self.Point
        elif _['max90'] is True:
            self.Patch.Analysis['max90'] = self.Point

        # [pi / 5, pi] doesn't give anything of interest
        if round(theta, d) == round(pi / 3, d):  # YES
            rs.AddPoint(self.Point)

        if round(theta, d) == round(pi / 4, d):  # YES
            rs.AddPoint(self.Point)

        if round(theta, d) == round(pi / 6, d):  # YES
            rs.AddPoint(self.Point)

        if self.Analysis['z1 == 0']:
            # rs.AddPoint(self.Point)
            pass
        if self.Analysis['z2 == 0']:
            # rs.AddPoint(self.Point)
            pass
        if self.Analysis['z0 == 0']:  # YES
            # rs.AddPoint(self.Point)
            pass
        if self.Analysis['z0 == 1']:
            # rs.AddPoint(self.Point)
            pass
        if self.Analysis['z0 == -1']:
            # rs.AddPoint(self.Point)
            pass

        return _

    def AddPatch(self, *args):
        '''
        Add `self.n ** 2`th Patch
        '''
        self.Patch = Patch(self, args[:2])
        self.Patches.append(self.Patch)
        self.PatchCount += 1

        return self.Patch

    def BuildPoint(self, *args):
        '''
        Calculate point coordinates and return Rhino.Geometry.Point3d
        '''
        k1, k2, a, b = args

        coords = map(
            lambda i: (i * self.Scale),
            CalculatePoint(self.n, self.Alpha, *args)  # args[1:]
        )
        x, y, z = coords

        OffsetX, OffsetY = self.Offset
        coords[0] = x + OffsetX
        coords[1] = y + OffsetY

        self.Point = Point3d(*coords)
        self.Points.Add(self.Point)
        self.Patch.Points.Add(self.Point)
        self.PointCount += 1

        self.PointAnalysis(*args)

        return self.Point

    @staticmethod
    def BuildInterpolatedCurve(points):
        '''
        TODO rescue Exception raised if insufficient points

        [](http://developer.rhino3d.com/samples/rhinocommon/surface-from-edge-curves/)
        `rs.AddInterpCurve`
        '''
        points = rs.coerce3dpointlist(points, True)

        degree = 3

        start_tangent = Vector3d.Unset
        start_tangent = rs.coerce3dvector(start_tangent, True)

        end_tangent = Vector3d.Unset
        end_tangent = rs.coerce3dvector(end_tangent, True)

        knotstyle = System.Enum.ToObject(CurveKnotStyle, 0)

        curve = Curve.CreateInterpolatedCurve(
            points,
            degree,
            knotstyle,
            start_tangent,
            end_tangent
        )

        if curve:
            return curve

        raise Exception('Unable to CreateInterpolatedCurve')

    @staticmethod
    def Colour(n, k1, k2):
        '''
        Returns phase keyed RGB colour weighted by phase displacement in
        z1 (green) and in z2 (blue) from the fundamental domain (white).
        '''
        i = 255 / n

        if k1 == k2 == 0:
            r = 255  # 0
            g = 255  # 0
            b = 255
        else:
            r = 0  # i * (k1 + 1)
            g = i * (k1 + 1)
            b = i * (k2 + 1)

        return Color.FromArgb(r, g, b)

    def __rendered__(self, obj):
        '''
        Confirm `obj` present in document Guid
        '''
        if obj == System.Guid.Empty:
            raise Exception('RenderError')

        return True

    def Render(self, cb, group, *args, **kwargs):
        '''
        Evaluates `cb()` and assigns Geometry to patch layer.
        '''
        ids = []

        for k1, phase in enumerate(utility.chunk(self.Patches, self.n)):
            parent = rs.AddLayer('::'.join([group, str(k1)]))

            for k2, patch in enumerate(phase):
                layer = rs.AddLayer('::'.join([parent, str(k2)]), self.Colour(self.n, k1, k2))
                cb(phase, patch, layer, ids)

        doc.Views.Redraw()

        return ids

    def Surfaces(self):
        return map(lambda e: e.Surfaces, self.Patches)

    def Breps(self):
        return map(lambda e: e.Brep, self.Patches)

    def Edges(self):
        return map(lambda e: e.Edges, self.Patches)

    def Meshes(self):
        return [self.MeshA, self.MeshB]


class PointCloudBuilder(Builder):
    __slots__ = Builder.__slots__

    def __init__(self, *args):
        Builder.__init__(self, *args)

    def Render(self, *args):
        parent = rs.AddLayer('Points')

        def cb(phase, patch, layer, ids):
            for point in patch.Points:
                id = doc.Objects.AddPoint(point)
                ids.append(id)
                rs.ObjectLayer(id, layer)

        Builder.Render(self, cb, parent, *args)


class MeshBuilder(Builder):
    __slots__ = Builder.__slots__ + ['MeshA', 'MeshB', 'MeshCount']

    def __init__(self, *args):
        Builder.__init__(self, *args)
        self.MeshA = None
        self.MeshB = None
        self.MeshCount = 0

    def __listeners__(self):
        listeners = Builder.__listeners__(self)
        listeners['k2.on'].append(self.AddMesh)
        listeners['b.on'].append(self.IncrementMeshCount)
        listeners['b.in'].append(self.BuildMesh)
        listeners['k2.out'].append(self.WeldMesh)

        return listeners

    def AddMesh(self, *args):
        # k1, k2 = args

        self.Patch.MeshA = Mesh()
        self.Patch.MeshB = Mesh()

    def IncrementMeshCount(self, *args):
        k1, k2, a, b = args

        if a == self.RngU[0] and k2 == self.RngK[0] and k1 == self.RngK[0]:
            self.MeshCount += 1

    def BuildFaces(self, mesh, k1, k2, a, b):
        for i in [
            self.PointCount,
            (self.PointCount - 1),
            (self.PointCount - self.MeshCount - 1),
            (self.PointCount - self.MeshCount)
        ]:
            try:  # account for 0 index
                p = self.Points[i - 1]
                mesh.Vertices.Add(p.X, p.Y, p.Z)
            except IndexError:
                print 'Points[' + str(i) + '] out of range, ' + str(self.PointCount)

        mesh.Faces.AddFace(0, 1, 2, 3)
        mesh.Normals.ComputeNormals()
        mesh.Compact()

    def BuildMesh(self, *args):
        k1, k2, a, b = args

        if a > self.RngU[0] and b > self.RngV[0]:
            if a <= self.RngU[self.CentreU]:
                self.MeshA = Mesh()
                self.BuildFaces(self.MeshA, *args)
                self.Patch.MeshA.Append(self.MeshA)
            else:
                self.MeshB = Mesh()
                self.BuildFaces(self.MeshB, *args)
                self.Patch.MeshB.Append(self.MeshB)

    def WeldMesh(self, *args):
        self.Patch.MeshA.Weld(pi)
        self.Patch.MeshB.Weld(pi)

    def Render(self, *args):
        parent = rs.AddLayer('Meshes')

        def cb(phase, patch, layer, ids):
            for i, mesh in enumerate([patch.MeshA, patch.MeshB]):
                id = doc.Objects.AddMesh(mesh)
                ids.append(id)
                rs.ObjectLayer(id, layer)

        Builder.Render(self, cb, parent, *args)


class CurveBuilder(Builder):
    __slots__ = Builder.__slots__ + [
        'Edges',
        'A', 'B', 'C', 'D',
        'A1', 'B1', 'C1', 'D1',
        'A2', 'B2', 'C2', 'D2'
    ]

    def __init__(self, *args):
        Builder.__init__(self, *args)

    def __listeners__(self):
        listeners = Builder.__listeners__(self)
        listeners['k2.in'].append(self.AddEdges)
        listeners['b.in'].append(self.PlotEdges)
        listeners['k2.out'].extend([self.BuildEdges])

        return listeners

    def AddEdges(self, *args):
        # "rails"
        self.A = []
        self.C = []

        self.A1 = []
        self.A2 = []

        self.C1 = []
        self.C2 = []

        # "cross-sections"
        self.B = []
        self.D = []

        self.B1 = []
        self.B2 = []

        self.D1 = []
        self.D2 = []

    def PlotEdges(self, *args):
        '''
        [#10](https://bitbucket.org/kunst_dev/snippets/issues/10/curve-generation)
        '''
        k1, k2, a, b = args

        # "rails"
        if a == self.RngU[0]:  # self.Analysis['min90']:
            self.A.append(self.Point)
            self.A1.append(self.Point)

        if a == self.RngU[self.CentreU]:  # self.Analysis['mid90']:
            self.C1.append(self.Point)
            self.C2.append(self.Point)

        if a == self.RngU[-1]:  # self.Analysis['max90']:
            self.C.append(self.Point)
            self.A2.append(self.Point)

        # "cross-sections"
        if b == self.RngV[0]:
            self.B.append(self.Point)

            if len(self.B1) <= self.CentreV:
                self.B1.append(self.Point)
            if len(self.B1) > self.CentreV:
                self.B2.append(self.Point)

        if b == self.RngV[-1]:
            self.D.append(self.Point)
            if len(self.D1) <= self.CentreV:
                self.D1.append(self.Point)
            if len(self.D1) > self.CentreV:
                self.D2.append(self.Point)

    def BuildEdges(self, *args):
        Edges = CurveList()
        Edges1 = CurveList()
        Edges2 = CurveList()

        # "rails"
        for points in (self.A, self.C):
            Edges.Add(Builder.BuildInterpolatedCurve(points))

        # "cross-sections"
        for points in (self.B, self.D):
            Edges.Add(Builder.BuildInterpolatedCurve(points))

        # Sub-division "rails"
        for points in (self.A1, self.C1):
            Edges1.Add(Builder.BuildInterpolatedCurve(points))
        for points in (self.A2, self.C2):
            Edges2.Add(Builder.BuildInterpolatedCurve(points))

        # Sub-division "cross-sections"
        for points in (self.B1, self.D1):
            Edges1.Add(Builder.BuildInterpolatedCurve(points))
        for points in (self.B2, self.D2):
            Edges2.Add(Builder.BuildInterpolatedCurve(points))

        self.Patch.Edges = [Edges, Edges1, Edges2]

    def DemarcateCurveCentre(self, text, curve, layer='Centre'):
        centre = curve.PointAtNormalizedLength(0.5)
        id = rs.AddTextDot(text, centre)
        rs.ObjectLayer(id, layer)

    def Render(self, *args):
        # rs.AddLayer('Centre', Color.Magenta)
        parent = rs.AddLayer('Curves')

        for k1, phase in enumerate(utility.chunk(self.Patches, self.n)):
            for k2, patch in enumerate(phase):
                Edges, Edges1, Edges2 = patch.Edges
                A, C, B, D = Edges
                A1, C1, B1, D1 = Edges1
                A2, C2, B2, D2 = Edges2

                for e in (1, 2):
                    for i, char in enumerate(('A', 'C', 'B', 'D')):
                        var = char + str(e)
                        colour = self.__palette__[-k1][i]
                        layer = rs.AddLayer('::'.join([parent, var]), colour)

                        curve = eval(var)
                        id = doc.Objects.AddCurve(curve)
                        self.__rendered__(id)
                        rs.ObjectLayer(id, layer)

                        # self.DemarcateCurveCentre('[' + str(k1) + ',' + str(k2) + ']', curve)

                # for edgeGroup in (Edges1, Edges2):
                #     # Create Boundary Representation
                #     # self.Patch.Brep = Brep.CreateEdgeSurface(edgeGroup)
                #     # id = doc.Objects.AddBrep(self.Patch.Brep)
                #     # self.__rendered__(id)
                #
                #     # Create Nurbs Surface from curves
                #     surface, err = NurbsSurface.CreateNetworkSurface(
                #         edgeGroup,
                #         1,
                #         0.1,
                #         0.1,
                #         1.0
                #     )
                #     id = doc.Objects.AddSurface(surface)
                #     self.__rendered__(id)


class SurfaceBuilder(CurveBuilder):
    '''
    Build quadrilateral surfaces.
    See [Example](https://bitbucket.org/snippets/kunst_dev/X894E8)
    '''

    __slots__ = CurveBuilder.__slots__ + [
        '__points__',
        'UCount', 'VCount'
    ]

    def __init__(self, *args):
        CurveBuilder.__init__(self, *args)
        # Note: Polysurface created if U and V degrees differ.
        self.UCount = 0
        self.VCount = 0

    def __listeners__(self):
        listeners = CurveBuilder.__listeners__(self)
        listeners['k2.on'].append(self.AddSurface)
        listeners['a.on'].append(self.ResetVCount)
        listeners['b.in'].append(self.PlotSurface)
        listeners['b.out'].append(self.IncrementVCount)
        listeners['a.out'].extend([
            self.IncrementUCount,
            self.AddSurfaceSubdivision
        ])
        listeners['k2.out'].extend([self.BuildSurface, self.JoinSurfaces])

        return listeners

    def AddSurface(self, *args):
        self.__points__ = Point3dList()
        self.ResetUCount()
        self.ResetVCount()

    def ResetUCount(self, *args):
        self.UCount = 0

    def ResetVCount(self, *args):
        self.VCount = 0

    def IncrementVCount(self, *args):
        self.VCount += 1

    def IncrementUCount(self, *args):
        self.UCount += 1

    def AddSurfaceSubdivision(self, *args):
        k1, k2, a = args

        if self.Analysis['mid90']:  # a == self.RngU[self.CentreU]
            self.BuildSurface(*args)  # Finalise current subdivision
            self.AddSurface(*args)  # Begin next subdivision
            self.__points__ = Point3dList(self.Points[-self.U:])
            self.IncrementUCount()

    def PlotSurface(self, *args):
        k1, k2, a, b = args

        self.__points__.Add(self.Point)

    def BuildSurface(self, *args):
        '''
        TODO Add `Weight` to `self.Patch.Analysis['centre']` control point

        ```
            cp = surface.Points.GetControlPoint(0, self.V / 2)
            cp.Weight = 1000
            for point in surface.Points:
                if point.X == 0 or point.Y == 0:
                    cp = ControlPoint(point.X, point.Y, point.Z, 1000)
                    surface.Points.SetControlPoint(0, self.V / 2, cp)
        ```
        '''
        surface = NurbsSurface.CreateFromPoints(
            self.__points__,
            self.UCount,
            self.VCount,
            self.UDegree,
            self.VDegree
        )

        self.Patch.Surfaces.append(surface)

    def JoinSurfaces(self, *args):
        '''
        TODO Join Patch subdivisions
        Increase `doc.ModelAbsoluteTolerance` to maximise polysurface inclusion
        '''
        return
        # rs.JoinSurfaces(self.Patch.Surfaces[-2:])

    def Check(self):
        curveData = []
        tolerance = doc.ModelAbsoluteTolerance
        rs.UnitAbsoluteTolerance(0.1, True)

        def results(obj):
            if obj is None:
                # print 'Selected curves do not intersect.'
                return

            for intersection in obj:
                if intersection[0] == 1:
                    # print 'Intersection point on first curve: ', intersection[1]
                    rs.AddPoint(intersection[1])
                    # print 'Intersection point on second curve: ', intersection[3]
                    rs.AddPoint(intersection[3])
                    # print 'First curve parameter: ', intersection[5]
                    # print 'Second curve parameter: ', intersection[7]
                else:
                    # print 'Intersection start point on first curve: ', intersection[1]
                    rs.AddPoint(intersection[1])
                    # print 'Intersection end point on first curve: ', intersection[2]
                    rs.AddPoint(intersection[2])
                    # print 'Intersection start point on second curve: ', intersection[3]
                    # print 'Intersection end point on second curve: ', intersection[4]
                    # print 'First curve parameter range: ', intersection[5], ' to ', intersection[6]
                    # print 'Second curve parameter range: ', intersection[7], ' to ', intersection[8]

        for k1, phase in enumerate(utility.chunk(self.Patches, self.n)):
            for k2, patch in enumerate(phase):
                _, Edges1, Edges2 = patch.Edges
                A1, C1, B1, D1 = Edges1
                A2, C2, B2, D2 = Edges2

                for i in (1, 2):
                    arr = ('A' + str(i), 'B' + str(i), 'C' + str(i), 'D' + str(i))

                    for e in arr:
                        curve = eval(e)
                        doc.Objects.AddCurve(curve)
                        # result = Intersect.Intersection.CurveCurve(a, b, tolerance, 0.1)
                        result = rs.CurveCurveIntersection(curve)
                        results(result)

                    for pair in combinations(arr, 2):
                        a, b = pair
                        # result = Intersect.Intersection.CurveCurve(a, b, tolerance, 0.1)
                        result = rs.CurveCurveIntersection(eval(a), eval(b))
                        results(result)

    def Render(self, *args):
        parent = rs.AddLayer('Surfaces')

        self.Check()

        def cb(phase, patch, layer, ids):
            for i, surface in enumerate(patch.Surfaces):
                id = doc.Objects.AddSurface(surface)
                self.__rendered__(id)
                ids.append(id)
                rs.ObjectLayer(id, layer)

        Builder.Render(self, cb, parent, *args)


__builders__ = {
    1: PointCloudBuilder,
    2: MeshBuilder,
    3: CurveBuilder,
    4: SurfaceBuilder
}
