import cmath
from math import cos, sin, pi, fabs
from itertools import combinations
import string
import System.Guid
import System.Drawing
import System.Enum
from System.Drawing import Color
from scriptcontext import doc, sticky
# from rhinoscriptsyntax import GetBoolean, GetInteger,
#   GetReal, AddObjectsToGroup, AddGroup, frange
import rhinoscriptsyntax as rs
from Rhino.Geometry import Brep, BrepFace, ControlPoint, Curve, CurveKnotStyle, Mesh, NurbsCurve, NurbsSurface, Point3d, Vector3d, Intersect
from Rhino.Collections import Point3dList, CurveList
import Rhino
import utility
import export
from export import fname
from events import EventHandler


reload(utility)
reload(export)


log = open('./log.txt', 'w')


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
    '''
    Parameters:
        n : int
        deg : float
        step : float
        scale : int
        offset : int
        type : int
            [1] generate Rhino.Geometry.Point
            [2] generate Rhino.Geometry.Mesh
            [3] generate Rhino.Geometry.Curve
            [4] generate Rhino.Geometry.Surface
    '''
    if rs.ContextIsRhino():  # rs.ContextIsGrasshopper()
        args = GetUserInput()

    # n, deg, step, scale, offset, type = args
    type = args[-1]

    if type == 5:
        pass
    elif type is None:
        raise Exception('Builder not specified')
    else:
        type = __builders__[type]

        # Cache builder instance
        sticky['builder'] = type(*args[:-1])
        sticky['builder'].Build()
        sticky['builder'].Finalize()


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
        'Brep', 'Breps',
        'MeshA', 'MeshB',
        'Edges'
    ]

    def __init__(self, cy, phase):
        self.CalabiYau = cy
        self.Phase = phase
        self.Analysis = {}
        self.Points = Point3dList()
        self.Surfaces = []
        self.Breps = []
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
        ndigits : int
            Rounding
        U : int
        V : int
        Degree : int
        UDegree : int
        VDegree : int
        UCount : int
        VCount : int
        MinU : float
        MidU : float
        MaxU : float
        MinV : float
        MidV : float
        MaxV : float
        StepV : float
        RngK : range
        RngU : range
        RngV : range
        __builder__ : class
        __palette__ : list<list<System.Drawing.Color>>
        Analysis : dict
        Rendered : dict
        BoundingBox : list
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
                 'ndigits',
                 'U', 'V',
                 'Degree', 'UDegree', 'VDegree',
                 'UCount', 'VCount',
                 'MinU', 'MidU', 'MaxU', 'StepU', 'CentreU',
                 'MinV', 'MidV', 'MaxV', 'StepV', 'CentreV',
                 'RngK', 'RngU', 'RngV',
                 'Analysis',
                 'Rendered',
                 'BoundingBox',
                 'Points', 'Point', 'PointCount',
                 'Patches', 'Patch', 'PatchCount',
                 '__builder__',
                 '__palette__']

    def __init__(self, n=1, deg=1.0, step=0.1, scale=1, offset=(0, 0)):
        '''
        Parameters:
            n : int
            deg : float
            step : float
            scale : int
            offset : int
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

        self.Degree = self.VDegree = self.UDegree = 3

        # Note: Polysurface created if U and V degrees differ.
        self.VCount = self.UCount = 0

        self.MinU = -1
        self.MaxU = 1
        self.MidU = (self.MinU + self.MaxU) / 2.0  # 0
        # deduct 1 to accomodate `rs.frange` zero offset
        self.StepU = fabs(self.MaxU - self.MinU) / (self.U - 1.0)

        self.MinV = 0
        self.MaxV = float(pi / 2)
        self.MidV = (self.MinV + self.MaxV) / 2.0  # pi / 4
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
        self.Analysis.update({
            '15': round(pi / 12, self.ndigits),
            '30': round(pi / 6, self.ndigits),
            '45': round(pi / 4, self.ndigits),
            '60': round(pi / 3, self.ndigits),
            '75': round(pi / 2.4, self.ndigits),
            '90': round(pi / 2, self.ndigits),
            'midU': round(self.MidU, self.ndigits),
            'midV': round(self.MidV, self.ndigits),
            'g': Genus(self.n),
            'chi': EulerCharacteristic(self.n)
        })

        self.Rendered = {}

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
        self.Events.register(self.__listeners__())

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

        self.Render()

    def Finalize(self):
        return

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
        z0 = round(_['z0'].imag, d)
        z1 = round(_['z1'].imag, d)
        z2 = round(_['z2'].imag, d)
        _['z0 == 0'] = z0 == 0
        _['z0 == 1'] = z0 == 1
        _['z0 == -1'] = z0 == -1
        _['z1 == 0'] = z1 == 0
        _['z2 == 0'] = z2 == 0

        # Intervals through self.RngU
        xi = _['xi'] = _['U'] = round(xi, d)
        _['xi == minU'] = xi == self.MinU  # -1
        _['xi < midU'] = xi < _['midU']
        _['xi <= midU'] = xi <= _['midU']
        _['xi == midU'] = xi == _['midU']
        _['xi >= midU'] = xi >= _['midU']
        _['xi > midU'] = xi > _['midU']
        _['xi == maxU'] = xi == self.MaxU  # 1

        # Intervals through self.RngV
        theta = _['theta'] = _['V'] = round(theta, d)
        _['theta == 0'] = theta == float(0)  # self.MinV
        _['theta == 15'] = theta == _['15']
        _['theta <= 30'] = theta <= _['30']
        _['theta == 30'] = theta == _['30']
        _['theta >= 30'] = theta >= _['30']
        _['theta < 45'] = theta < _['45']
        _['theta <= 45'] = theta <= _['45']
        _['theta == 45'] = theta == _['45']
        _['theta >= 45'] = theta >= _['45']
        _['theta > 45'] = theta > _['45']
        _['theta <= 60'] = theta <= _['60']
        _['theta == 60'] = theta == _['60']
        _['theta >= 60'] = theta >= _['60']
        _['theta == 75'] = theta == _['75']
        _['theta <= 90'] = theta <= _['90']
        _['theta == 90'] = theta == _['90']  # self.MaxV

        # The junction of n patches is a fixed point of a complex phase transformation.
        # The n curves converging at this fixed point emphasize the dimensions of the surface.
        # _['min0'] = _['xi == minU'] and _['theta == 0']
        # # _['mid0'] = _['z1 == 0'] or _['z2 == 0'] and _['xi == midU']
        # _['mid0'] = _['xi == midU'] and _['theta == 0']
        # _['max0'] = _['xi == maxU'] and _['theta == 0']
        #
        # _['min45'] = _['xi == minU'] and _['theta == 45']
        # _['mid45'] = _['xi == midU'] and _['theta == 45']
        # _['max45'] = _['xi == maxU'] and _['theta == 45']
        #
        # _['min90'] = _['xi == minU'] and _['theta == 90']
        # _['mid90'] = _['xi == midU'] and _['theta == 90']
        # _['max90'] = _['xi == maxU'] and _['theta == 90']

        # if _['min0'] is True:
        #     self.Patch.Analysis['min0'] = self.Point
        # elif _['mid0'] is True:
        #     self.Patch.Analysis['centre'] = self.Patch.Analysis['mid0'] = self.Point
        # elif _['max0'] is True:
        #     self.Patch.Analysis['max0'] = self.Point
        #
        # elif _['min45'] is True:
        #     self.Patch.Analysis['min45'] = self.Point
        # elif _['mid45'] is True:
        #     self.Patch.Analysis['mid45'] = self.Point
        # elif _['max45'] is True:
        #     self.Patch.Analysis['max45'] = self.Point
        #
        # elif _['min90'] is True:
        #     self.Patch.Analysis['min90'] = self.Point
        # elif _['mid90'] is True:
        #     self.Patch.Analysis['mid90'] = self.Point
        # elif _['max90'] is True:
        #     self.Patch.Analysis['max90'] = self.Point

        return _

    def OffsetU(self, steps=1.0):
        return self.Analysis['U'] == round(self.MidU + (self.StepU * steps), 2)

    def OffsetV(self, steps=1.0):
        return self.Analysis['V'] == round(self.MidV + (self.StepV * steps), 2)

    def ResetUCount(self, *args):
        self.UCount = 0

    def ResetVCount(self, *args):
        self.VCount = 0

    def IncrementVCount(self, *args):
        self.VCount += 1

    def IncrementUCount(self, *args):
        self.UCount += 1

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
    def BuildInterpolatedCurve(points, degree=3):
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
    def FindCurveCentre(curve, text, layer='Centre'):
        centre = curve.PointAtNormalizedLength(0.5)
        id = rs.AddTextDot(text, centre)
        rs.ObjectLayer(id, layer)

        return id

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
                colour = self.Colour(self.n, k1, k2)
                layer = rs.AddLayer('::'.join([parent, str(k2)]), colour)
                cb(phase, patch, layer, ids)

        doc.Views.Redraw()

        return ids

    def AddLayers(self):
        layers = [
            'Points',
            'Meshes',
            'Curves',
            'Surfaces',
            'PolySurface',
            'Intersect::Curves',
            'Intersect::Points',
            'Border::All',
            'Border::Outer',
            # 'Silhouette',
            'Wireframe',
            'Wireframe::Outer',
            'Wireframe::U',
            'Wireframe::U::Divisions',
            'Wireframe::U::Divisions::EqiUnjoined',
            'Wireframe::U::Divisions::Eqi',
            'Wireframe::U::Divisions::Count',
            'Wireframe::U::Divisions::Length',
            'Wireframe::V',
            'Wireframe::V::Divisions',
            'Wireframe::V::Divisions::Count',
            # 'RenderMesh',
            'BoundingBox',
            'Camera',
            '2D'
        ]

        for str in ('01', '02', '03', '04', '05'):
            layer = ' '.join(['Layer', str])
            if rs.IsLayer(layer):
                rs.DeleteLayer(layer)

        for layer in layers:
            if not rs.IsLayer(layer):
                layer = rs.AddLayer(layer)
                rs.LayerPrintColor(layer, Color.Black)
                rs.LayerPrintWidth(layer, 0.4)  # mm
                # rs.LayerVisible(layer, False)

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

        if a == self.MinU and k2 == k1 == self.RngK[0]:
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

        if a > self.MinU and b > self.MinV:
            if self.Analysis['xi <= midU']:
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
    @staticmethod
    def RDiv():
        arr = []
        for char in list(string.digits)[:3]:
            arr.append('R' + char)

        return arr

    @staticmethod
    def XDiv():
        arr = []
        for char in list(string.digits)[:10]:
            arr.append('X' + char)

        return arr

    __slots__ = Builder.__slots__ + [
        'Curves',
        'CurveCombinations',
        'R', 'X',
        'Outer',
        'RDiv',
        'XDiv'
    ] + RDiv.__func__() + XDiv.__func__()

    def __init__(self, *args):
        Builder.__init__(self, *args)

        self.Curves = CurveList()
        self.CurveCombinations = None
        self.RDiv = CurveBuilder.RDiv()
        self.XDiv = CurveBuilder.XDiv()
        self.R = CurveList()
        self.X = CurveList()
        self.Outer = CurveList()

        # "rails"
        for div in self.RDiv:
            setattr(self, div, [])
        # "cross-sections"
        for div in self.XDiv:
            setattr(self, div, [])

    def __listeners__(self):
        listeners = Builder.__listeners__(self)
        listeners['k2.on'].append(self.AddEdges)
        listeners['b.in'].append(self.PlotEdges)
        listeners['k2.out'].append(self.BuildEdges)

        return listeners

    def CombineCurves(self):
        '''
        Returns unique curve pairs as enumerable itertools.combinations
        '''
        if self.CurveCombinations is None:
            self.CurveCombinations = combinations(self.Curves, 2)

        return self.CurveCombinations

    def AddEdges(self, *args):
        for div in self.RDiv:
            setattr(self, div, Point3dList())
        for div in self.XDiv:
            setattr(self, div, Point3dList())

    def PlotEdges(self, *args):
        '''
        [#10](https://bitbucket.org/kunst_dev/snippets/issues/10/curve-generation)
        '''
        k1, k2, a, b = args

        # "rails"
        if self.Analysis['xi == minU']:
            self.R2.Add(self.Point)
        elif self.Analysis['xi == midU']:
            self.R1.Add(self.Point)
        elif self.Analysis['xi == maxU']:
            self.R0.Add(self.Point)

        # "cross-sections"
        if self.Analysis['theta == 0']:
            if self.Analysis['xi <= midU']:
                self.X9.Add(self.Point)
            if self.Analysis['xi >= midU']:
                self.X8.Add(self.Point)
        elif self.Analysis['theta == 30']:
            if self.Analysis['xi <= midU']:
                self.X7.Add(self.Point)
            if self.Analysis['xi >= midU']:
                self.X6.Add(self.Point)
        elif self.Analysis['theta == 45']:
            if self.Analysis['xi <= midU']:
                self.X5.Add(self.Point)
            if self.Analysis['xi >= midU']:
                self.X4.Add(self.Point)
        elif self.Analysis['theta == 60']:
            if self.Analysis['xi <= midU']:
                self.X3.Add(self.Point)
            if self.Analysis['xi >= midU']:
                self.X2.Add(self.Point)
        elif self.Analysis['theta == 90']:
            if self.Analysis['xi <= midU']:
                self.X1.Add(self.Point)
            if self.Analysis['xi >= midU']:
                self.X0.Add(self.Point)

    def BuildEdges(self, *args):
        R = CurveList()
        X = CurveList()

        # "rails"
        for i, points in enumerate(map(lambda div: getattr(self, div), self.RDiv)):
            curve = Builder.BuildInterpolatedCurve(points, self.Degree)
            for collection in (R, self.R, self.Curves):
                collection.Add(curve)
            if i != 1:
                self.Outer.Add(curve)

        # "cross-sections"
        for i, points in enumerate(map(lambda div: getattr(self, div), self.XDiv)):
            curve = Builder.BuildInterpolatedCurve(points, self.Degree)
            for collection in (X, self.X, self.Curves):
                collection.Add(curve)

        self.Patch.Edges = (R, X)

    def Render(self, *args):
        def cb(curve, layer):
            id = doc.Objects.AddCurve(curve)
            self.__rendered__(id)
            rs.ObjectLayer(id, layer)
            self.Rendered['Curves'].append(id)

            # Builder.FindCurveCentre(curve, '[' + str(k1) + ',' + str(k2) + ']')

        self.Rendered['Curves'] = []
        group = rs.AddLayer('Curves')

        for k1, phase in enumerate(utility.chunk(self.Patches, self.n)):
            parent = rs.AddLayer('::'.join([group, str(k1)]))

            for k2, patch in enumerate(phase):
                R, X = patch.Edges
                R0, R1, R2 = R
                X0, X1, X2, X3, X4, X5, X6, X7, X8, X9 = X

                # colour = self.__palette__[-k2][-1]
                colour = self.Colour(self.n, k1, k2)
                layer = rs.AddLayer('::'.join([parent, str(k2)]), colour)

                for div in self.RDiv:
                    curve = eval(div)
                    cb(curve, layer)

                for div in self.XDiv:
                    curve = eval(div)
                    cb(curve, layer)

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
    @staticmethod
    def Div():
        arr = []
        for i in range(0, 2, 1):
            for char in range(0, 90 + 15, 15):
                arr.append('S' + str(char) + '_' + str(i))

        return arr

    @staticmethod
    def UDiv():
        arr = []
        for i in range(0, 2, 1):
            for char in range(0, 90 + 15, 15):
                arr.append('U' + str(char) + '_' + str(i))

        return arr

    @staticmethod
    def VDiv():
        arr = []
        for i in range(0, 2, 1):
            for char in range(0, 90 + 15, 15):
                arr.append('V' + str(char) + '_' + str(i))

        return arr

    __slots__ = CurveBuilder.__slots__ + [
        '__points__',
        'Surfaces',
        'Breps',
        'SurfaceCombinations',
        'BrepCombinations',
        'PolySurface',
        'Div',
        'UDiv',
        'VDiv'
    ] + Div.__func__() + UDiv.__func__() + VDiv.__func__()

    def __init__(self, *args):
        CurveBuilder.__init__(self, *args)

        self.Surfaces = []
        self.Breps = []
        self.SurfaceCombinations = None
        self.BrepCombinations = None
        self.PolySurface = None
        self.Div = SurfaceBuilder.Div()
        self.UDiv = SurfaceBuilder.UDiv()
        self.VDiv = SurfaceBuilder.VDiv()

    def __listeners__(self):
        listeners = CurveBuilder.__listeners__(self)
        listeners['k2.on'].append(self.AddSurfaces)
        listeners['b.in'].append(self.PlotSurface)
        listeners['k2.out'].extend([self.BuildSurface, self.JoinSurfaces])

        return listeners

    def CombineSurfaces(self):
        '''
        Returns unique Surface pairs as enumerable itertools.combinations
        '''
        if self.SurfaceCombinations is None:
            self.SurfaceCombinations = combinations(self.Surfaces, 2)

        return self.SurfaceCombinations

    def CombineBreps(self):
        '''
        Returns unique Brep pairs as enumerable itertools.combinations
        '''
        if self.BrepCombinations is None:
            self.BrepCombinations = combinations(self.Breps, 2)

        return self.BrepCombinations

    def AddSurfaces(self, *args):
        for div in self.Div:
            setattr(self, div, Point3dList())
        for div in self.UDiv:
            setattr(self, div, 0)
        for div in self.VDiv:
            setattr(self, div, 0)

    def AddSurfaceSubdivision(self, *args):
        '''
        Example:
            Make further U divisions as below:
            ```
            xi == self.RngU[self.CentreU]
            self.Analysis['midU']
            self.OffsetU(-3.0)
            self.OffsetU(3.0)
            ```
        '''
        k1, k2, a, b = args

        if self.Analysis['theta == 90']:
            if self.Analysis['midU']:
                self.BuildSurface(*args)  # Finalise current subdivision
                self.AddSurface(*args)  # Begin next subdivision
                self.__points__ = Point3dList(self.Points[-28:])
                self.IncrementUCount()

    def PlotSurface(self, *args):
        k1, k2, a, b = args

        if self.Analysis['theta <= 30']:
            if self.Analysis['xi == minU']:
                self.V0_0 += 1
            elif self.Analysis['xi == midU']:
                self.V0_1 += 1

            if self.Analysis['xi <= midU']:
                self.S0_0.Add(self.Point)
            if self.Analysis['xi >= midU']:
                self.S0_1.Add(self.Point)

        if self.Analysis['theta >= 30'] and self.Analysis['theta <= 45']:
            if self.Analysis['xi == minU']:
                self.V30_0 += 1
            elif self.Analysis['xi == midU']:
                self.V30_1 += 1

            if self.Analysis['xi <= midU']:
                self.S30_0.Add(self.Point)
            if self.Analysis['xi >= midU']:
                self.S30_1.Add(self.Point)

        if self.Analysis['theta >= 45'] and self.Analysis['theta <= 60']:
            if self.Analysis['xi == minU']:
                self.V45_0 += 1
            elif self.Analysis['xi == midU']:
                self.V45_1 += 1

            if self.Analysis['xi <= midU']:
                self.S45_0.Add(self.Point)
            if self.Analysis['xi >= midU']:
                self.S45_1.Add(self.Point)

        if self.Analysis['theta >= 60'] and self.Analysis['theta <= 90']:
            if self.Analysis['xi == minU']:
                self.V60_0 += 1
            elif self.Analysis['xi == midU']:
                self.V60_1 += 1

            if self.Analysis['xi <= midU']:
                self.S60_0.Add(self.Point)
            if self.Analysis['xi >= midU']:
                self.S60_1.Add(self.Point)

    def BuildSurface(self, *args):
        '''
        TODO Add `Weight` to `self.Patch.Analysis['centre']` control point

        NurbsSurface.CreateFromPoints will raise "Invalid U and V counts" if
        `Point3dList != self.UCount * self.VCount`

        ```
            cp = surface.Points.GetControlPoint(0, self.V / 2)
            cp.Weight = 1000
            for point in surface.Points:
                if point.X == 0 or point.Y == 0:
                    cp = ControlPoint(point.X, point.Y, point.Z, 1000)
                    surface.Points.SetControlPoint(0, self.V / 2, cp)
        ```
        '''
        UCount = round(self.U / 2.0)

        for i in range(0, 2, 1):
            for char in range(0, 90 + 15, 15):
                points = getattr(self, 'S' + str(char) + '_' + str(i))
                if points.Count > 0:
                    srf = NurbsSurface.CreateFromPoints(
                        points,
                        UCount,
                        getattr(self, 'V' + str(char) + '_' + str(i)),
                        self.UDegree,
                        self.VDegree
                    )

                    self.Surfaces.append(srf)
                    self.Patch.Surfaces.append(srf)

                    brep = Brep.TryConvertBrep(srf)
                    self.Breps.append(brep)
                    self.Patch.Breps.append(brep)

    def JoinSurfaces(self, *args):
        '''
        TODO Join Patch subdivisions
        Increase `doc.ModelAbsoluteTolerance` to maximise polysurface inclusion
        '''
        pass

        tolerance = 0.1

        result = Brep.JoinBreps(self.Patch.Breps, tolerance)
        # for srf in result:
        #     id = doc.Objects.AddBrep(srf)
        #     self.__rendered__(id)
        #     rs.ObjectLayer(id, 'PolySurface')

        return result

    def Render(self, *args):
        def cb(phase, patch, layer, ids):
            for i, surface in enumerate(patch.Surfaces):
                id = doc.Objects.AddSurface(surface)
                self.__rendered__(id)
                ids.append(id)
                rs.ObjectLayer(id, layer)
                self.Rendered['Surfaces'].append(id)

        parent = rs.AddLayer('Surfaces')
        self.Rendered['Surfaces'] = []

        Builder.Render(self, cb, parent, *args)
        CurveBuilder.Render(self, *args)

    def Finalize(self):
        self.AddLayers()
        self.CombineCurves()
        self.CombineSurfaces()
        self.CombineBreps()
        self.BuildPolySurface()
        self.BuildBorders()
        # self.IntersectCurves()
        Curves, Points = self.IntersectSurfaces()
        # self.SplitAtIntersection()

        # self.DivideCurves()

        # self.BuildWireframe()
        # self.ConvertToBeziers()
        # self.BuildSilhouette()

        self.BuildBoundingBox()
        self.SetAxonometricCameraProjection()

        for layer in ('Camera', 'BoundingBox'):
            rs.LayerVisible(layer, False)
            rs.LayerLocked(layer, True)

        doc.Views.Redraw()

    def BuildPolySurface(self):
        tolerance = 0.1

        result = Brep.JoinBreps(self.Breps, tolerance)
        for srf in result:
            id = doc.Objects.AddBrep(srf)
            self.__rendered__(id)
            rs.ObjectLayer(id, 'PolySurface')

        self.PolySurface, = result
        return result

    def IntersectCurves(self):
        '''
        # Find intersections
        # Then draw a curve between points over the surface
        for k1, phase in enumerate(utility.chunk(self.Patches, self.n)):
            for k2, patch in enumerate(phase):

                for srf in patch.Surfaces:
                    rs.AddInterpCrvOnSrf(srf, points):
        '''
        def HandleIntersectionEvents(obj):
            if obj is None:
                return
            else:
                events = []
                for i in xrange(obj.Count):
                    event_type = 1
                    if (obj[i].IsOverlap):
                        event_type = 2
                    oa = obj[i].OverlapA
                    ob = obj[i].OverlapB
                    events.append((
                        event_type,
                        obj[i].PointA, obj[i].PointA2,
                        obj[i].PointB, obj[i].PointB2,
                        oa[0], oa[1],
                        ob[0], ob[1]
                    ))

            for e in events:
                if e[0] == 1:
                    for point in e[1:5]:
                        id = doc.Objects.AddPoint(point)
                        self.__rendered__(id)
                        rs.ObjectLayer(id, 'Intersect::Points')
                else:  # IsOverlap
                    pass
                    # rs.AddPoint(e[1])
                    # rs.AddPoint(e[2])

            return events

        tolerance = doc.ModelAbsoluteTolerance
        rs.UnitAbsoluteTolerance(0.1, True)

        # "self-intersections"
        for curve in self.Curves:
            result = Intersect.Intersection.CurveSelf(curve, 0.1)
            HandleIntersectionEvents(result)

        # "intersection"
        for combination in self.CurveCombinations:
            a, b = combination
            result = Intersect.Intersection.CurveCurve(a, b, 0.1, 1.0)
            HandleIntersectionEvents(result)

        rs.UnitAbsoluteTolerance(tolerance, True)  # restore tolerance

    def IntersectSurfaces(self):
        tolerance = doc.ModelAbsoluteTolerance

        Curves = CurveList()
        Points = Point3dList()

        for combination in self.BrepCombinations:
            a, b = combination

            result, curves, points = Intersect.Intersection.BrepBrep(a, b, tolerance)

            for point in points:
                Points.Add(point)
                id = doc.Objects.AddPoint(point)
                self.__rendered__(id)
                rs.ObjectLayer(id, 'Intersect::Points')

            for curve in curves:
                Curves.Add(curve)
                id = doc.Objects.AddCurve(curve)
                self.__rendered__(id)
                rs.ObjectLayer(id, 'Intersect::Curves')

        return Curves, Points

    def SplitAtIntersection(self):
        pass
        # breps = a.Split(b, tolerance)
        #
        # if len(breps) > 0:
        #     rhobj = rs.coercerhinoobject(a, True)
        #     if rhobj:
        #         attr = rhobj.Attributes if rs.ContextIsRhino() else None
        #         result = []
        #
        #         for i in range(len(breps)):
        #             if i == 0:
        #                 doc.Objects.Replace(rhobj.Id, breps[i])
        #                 result.append(rhobj.Id)
        #             else:
        #                 result.append(doc.Objects.AddBrep(breps[i], attr))
        #     else:
        #         result = [doc.Objects.AddBrep(brep) for brep in breps]

    def BuildBorders(self):
        # for curve in self.Curves:
        #     id = doc.Objects.AddCurve(curve)
        #     self.__rendered__(id)
        #     rs.ObjectLayer(curve, 'Border::All')

        for curve in Curve.JoinCurves(self.Outer):
            id = doc.Objects.AddCurve(curve)
            self.__rendered__(id)
            rs.ObjectLayer(id, 'Border::Outer')

    def BuildBoundingBox(self):
        self.BoundingBox = rs.BoundingBox(self.PolySurface)

        for i, pt in enumerate(self.BoundingBox):
            # id = doc.Objects.AddTextDot(str(i), p)
            id = doc.Objects.AddPoint(pt)
            rs.ObjectLayer(id, 'BoundingBox')

        return self.BoundingBox

    def SetAxonometricCameraProjection(self):  # Isometric
        bx = self.BoundingBox
        ln = rs.AddLine(bx[4], bx[2])
        rs.ObjectLayer(ln, 'Camera')
        rs.MoveObject(ln, bx[4] - bx[2])
        ln = rs.coerceline(ln)

        rs.ViewProjection('Perspective', 1)
        rs.ViewCameraTarget('Perspective', ln.From, ln.To)
        rs.ZoomBoundingBox(bx, all=True)
        rs.AddNamedView('Base', 'Perspective')

    def BuildWireframe():
        pass

        for i in range(1, 5, 1):
            layer = 'Wireframe::' + str(i)
            if not rs.IsLayer(layer):
                rs.AddLayer(layer, Color.Black)
            rs.LayerVisible(layer, False)

            for srf in self.PolySurface:
                obj = rs.coercerhinoobject(srf, True, True)
                obj.Attributes.WireDensity = i
                obj.CommitChanges()

            rs.ObjectsByType(rs.filter.polysurface, True)
            rs.Command(
                '_ExtractWireframe'
                + ' OutputLayer=Input'
                + ' GroupOutput=Yes'
                + ' _Enter'
            )

            for id in rs.LastCreatedObjects(True):
                rs.ObjectLayer(id, layer)

            rs.LayerLocked(layer, True)
        rs.LayerLocked('Wireframe', True)

    def ConvertToBeziers():
        pass

        layer = rs.AddLayer('Beziers')
        beziers = []

        # for srf in self.Surfaces:
        #     bezier = Rhino.ConvertSurfaceToBezier(srf, False)
        #     beziers.append(bezier)
        #     rs.ObjectLayer(bezier, layer)

        # rs.ObjectsByType(rs.filter.polysurface, True)
        # rs.Command('ConvertToBeziers')

        rs.LayerLocked(layer, True)

        return beziers

    def BuildSilhouette():
        pass

        rs.CurrentLayer('PolySurface')
        rs.Command('_Silhouette')
        for id in rs.ObjectsByType(rs.filter.curve, True):
            rs.ObjectLayer(id, 'Silhouette')
        rs.LayerLocked('Silhouette', True)

    def ExtractIsoCurve(self, srf, parameter, direction=0):
        def render(curves, layer):
            for curve in curves:
                id = doc.Objects.AddCurve(curve)
                self.__rendered__(id)
                rs.ObjectLayer(id, layer)

        isBrep = type(srf) is BrepFace
        U = []
        V = []

        for i, args in enumerate((('U', 1), ('V', 0))):
            direction = args[0]
            parameter = parameter[args[1]]
            arr = eval(direction)
            layer = '::'.join(['Wireframe::', direction])

            if direction in (i, 2):
                if isBrep:
                    arr.extend(srf.TrimAwareIsoCurve(0, parameter))
                else:
                    arr.append(srf.IsoCurve(0, parameter))
                render(arr, layer)

        return U, V

    def DivideCurves(self):
        # TODO
        #   * Join U
        #   * Join V
        #   * Find intersections
        #   * CrvThrough intersection pts
        #   * Split surfaces at self intersection

        sequence = {}
        # StartV = []
        for k1, phase in enumerate(utility.chunk(self.Patches, self.n)):
            # NextV = []
            # Connects at 0::0, 1::0, 2::0 but the continuity is really awkward
            for k2, patch in enumerate(phase):
                R, X = patch.Edges
                R0, R1, R2 = R
                X0, X1, X2, X3, X4, X5, X6, X7, X8, X9 = X

                # TODO
                #   * Order surfaces by smpathetic connection
                #   Find the next Surface in visual order
                #   Use IntersectSurfaces instead
                srf = patch.Surfaces[1]
                point = X9.PointAtStart
                end = X9.PointAtEnd

                rs.AddTextDot('X9E', end)
                rs.AddTextDot('X9S', point)

                for other in self.Surfaces:
                    if other != srf:
                        result = Intersect.Intersection.CurveSurface(X9, other, 0.1, 0.1)

                        # brep = Brep.TryConvertBrep(other)
                        # result, curves, points = Intersect.Intersection.CurveBrep(X9, brep)

                        # try:
                        #   result = rs.IsPointOnSurface(other, point)
                        # except:
                        #   result = False
                        if result:
                            for e in result:
                                if point == e.PointA2:
                                    sequence[e.PointA2] = [srf, other]
                                    # break
                            # break

                # self.Sequence = {}
                # seq = 0
                # if points:
                #     pass
                #     # self.Sequence[points[-1]] = (a, b)
                #     # seq += 1
                #     # rs.AddTextDot(str(), points[-1])
                #     #
                #     # for i, point in enumerate(self.Sequence.iterkeys()):
                #     #     a, b = self.Sequence[point]
                #     #     rs.AddTextDot(str(i), point)
                #
                # if curves:
                #     seq += 1
                #     point = curves[0].PointAtStart
                #     self.Sequence[point] = (a, b)
                #     rs.AddTextDot(str(seq), point)

                if k1 == k2 == 0:
                    divisions = X9.DivideByCount(5, True)
                    points = [X9.PointAt(t) for t in divisions]
                    srf = patch.Surfaces[1]
                    for point in points:
                        id = doc.Objects.AddPoint(point)
                        self.__rendered__(id)
                        rs.ObjectLayer(id, 'Wireframe::V::Divisions::Count')

                        parameter = rs.SurfaceClosestPoint(srf, point)
                        U, V = self.ExtractIsoCurve(srf, parameter, 1)
                        # for curve in V:
                        #     # start = curve.PointAtStart
                        #     # end = curve.PointAtEnd
                        #     NextV.append(curve.PointAtEnd)
                        #     StartV.append(curve.PointAtEnd)
                # elif k1 > 0 and k2 == 0:
                #     srf = patch.Surfaces[0]
                #     for point in StartV:
                #         parameter = rs.SurfaceClosestPoint(srf, point)
                #         U, V = self.ExtractIsoCurve(srf, parameter, 0)
                # else:
                #     srf = patch.Surfaces[0]
                #     prev = NextV
                #     NextV = []
                #     for point in prev:
                #         parameter = rs.SurfaceClosestPoint(srf, point)
                #         U, V = self.ExtractIsoCurve(srf, parameter, 0)
                #         for curve in V:
                #             NextV.append(curve.PointAtEnd)

                # points = R0.DivideEquidistant(5)
                # divisions = R0.DivideByLength(5, True)
                divisions = R0.DivideByCount(self.n * 10, True)
                points = [R0.PointAt(t) for t in divisions]
                srf = patch.Surfaces[1]
                NextU = []
                for point in points:
                    parameter = rs.SurfaceClosestPoint(srf, point)
                    U, V = self.ExtractIsoCurve(srf, parameter, 0)
                    for curve in U:
                        # start = curve.PointAtStart
                        # end = curve.PointAtEnd
                        NextU.append(curve.PointAtStart)

                srf = patch.Surfaces[0]
                for point in NextU:
                    parameter = rs.SurfaceClosestPoint(srf, point)
                    U, V = self.ExtractIsoCurve(srf, parameter, 0)

        for i, point in enumerate(sequence.iterkeys()):
            a, b = sequence[point]
            rs.AddTextDot(str(i), point)

        # srf = self.Surfaces[-1]
        #
        # for curve in self.Outer:
        #     points = curve.DivideEquidistant(5)
        #     for point in points:
        #         id = doc.Objects.AddPoint(point)
        #         self.__rendered__(id)
        #         rs.ObjectLayer(id, 'Wireframe::U::Divisions::EqiUnjoined')
        #
        # # When using the joined outer curves the intervals are consistent but curves no longer come together at xi == 0, theta == 0
        # for curve in Curve.JoinCurves(self.Outer):
        #     points = curve.DivideEquidistant(5)
        #     for point in points:
        #         id = doc.Objects.AddPoint(point)
        #         self.__rendered__(id)
        #         rs.ObjectLayer(id, 'Wireframe::U::Divisions::Eqi')
        #
        # for curve in Curve.JoinCurves(self.Outer):
        #     result = curve.DivideByCount(self.n * 10, True)
        #     points = [curve.PointAt(t) for t in result]
        #     for point in points:
        #         id = doc.Objects.AddPoint(point)
        #         self.__rendered__(id)
        #         rs.ObjectLayer(id, 'Wireframe::U::Divisions::Count')
        #
        # for curve in Curve.JoinCurves(self.Outer):
        #     result = curve.DivideByLength(5, True)
        #     points = [curve.PointAt(t) for t in result]
        #     for point in points:
        #         id = doc.Objects.AddPoint(point)
        #         self.__rendered__(id)
        #         rs.ObjectLayer(id, 'Wireframe::U::Divisions::Length')


__builders__ = {
    1: PointCloudBuilder,
    2: MeshBuilder,
    3: CurveBuilder,
    4: SurfaceBuilder
}
