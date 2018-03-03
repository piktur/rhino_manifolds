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
import Rhino.RhinoMath as rmath
from Rhino.Geometry import Brep, BrepFace, ControlPoint, Curve, CurveKnotStyle, Mesh, NurbsCurve, NurbsSurface, Point2d, Point3d, Vector3d, Intersect, Interval, Sphere
from Rhino.Collections import Point3dList, CurveList
import Rhino
import util
import export
from export import fname
from events import EventHandler


reload(util)
reload(export)


class Config:
    __slots__ = ['Log', 'Div', 'Defaults', '__density__']

    def __init__(self, **kwargs):
        self.Log = open(kwargs['log'], 'w')
        self.Div = kwargs['div']
        self.Defaults = kwargs['defaults']
        self.__density__ = {i: n for i, n in enumerate(kwargs['density'])}

    def GetNormalisedDensity(self, i):
        return self.__density__[i]

    def dig(self, attr, *args):
        '''
        Retrieves value from deeply nested attribute.

        Example:
            ```
            >>> __conf__.isOn('Div', 's', 0, 0)
            'S_0'

            >>> __conf__.isOn('Div', 's', 0)
            ['S_0']

            >>> __conf__.isOn(None)
            None
        '''
        try:
            attr = getattr(self, attr)
        except TypeError, AttributeError:
            pass

        for i, key in enumerate(args):
            if type(attr) == dict and attr.has_key(key):
                attr = attr[key]

                if i == len(args) - 1:
                    return attr
            else:
                try:
                    return attr[key]
                except IndexError:
                    pass

    def isOn(self, attr, *args):
        return self.dig(*args)

    def isOff(self, *args):
        return not self.dig(*args)

    @staticmethod
    def div1(prefix, *n):
        '''
        Returns list<str> representing divisions
        '''
        return [''.join((prefix, '_', str(i))) for i in range(*n)]

    @staticmethod
    def div2(*args):
        '''
        Returns list<str> representing surface divisions per 15 degree increment of theta
        '''
        arr = []
        maxV = int(round(rmath.ToDegrees(pi / 2.0), 1))  # 90 degrees
        stepV = int(round(rmath.ToDegrees(pi / 12.0), 1))  # 15 degrees

        for u in range(2):  # xi
            for v in range(0, maxV + stepV, stepV):  # theta
                arr.append(''.join([str(e) for e in args + (v, '_', u)]))

        return arr


__conf__ = Config(
    log='./log.txt',
    defaults={
        'n': 5,
        'deg': 0.25,
        'density': 2,
        'scale': 100,
        'offset': (0, 0)
    },
    density=(11, 21, 55, 107, 205),  # 110
    # Prepare variable names per division for each Geometry collection
    div={
        'c': {  # `CurveBuilder`
            2: {
                'R': Config.div1('R', 3),
                'X': Config.div1('X', 10)
                # 'U': Config.div1('U', 55),
                # 'V': Config.div1('V', 55)
            }
        },
        'm': {  # `MeshBuilder`
            1: Config.div1('M', 2)
        },
        's': {  # `SurfaceBuilder`
            # 0: Config.div1('S', 1),
            1: Config.div1('S', 1, 3),
            2: {
                k: v for (k, v) in zip(
                    ('S', 'U', 'V'),
                    [Config.div2(e) for e in ('S', 'U', 'V')]
                )
            }
        },
        'S': [1]  # `SurfaceBuilder.PolySurfaces`
    },
)


def GetUserInput():
    n = rs.GetInteger('n', 5, 1, 10)
    alpha = rs.GetReal('Degree', 0.25, 0.0, 2.0)
    density = rs.GetReal('UV Density', 2, 0, 4)
    scale = rs.GetInteger('Scale', 100, 1, 100)
    offset = rs.GetInteger('Offset', 0, -10, 10) * 300
    builder = rs.GetInteger('Geometry', 4, 1, 5)

    return {
        'n': n,
        'deg': alpha,
        'density': density,
        'scale': scale,
        'offset': (offset, offset),
        'type': builder
    }


def GenerateGrid(density=2, scale=100, type=4):
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


def Batch(dir, density=2, scale=100, type=4):
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


def Run(type=4, **kwargs):
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
        kwargs = GetUserInput()
        type = kwargs.pop('type')

    if type == 5:
        pass
    elif type is None:
        raise Exception('Builder not specified')
    else:
        type = __builders__[type]

        # Cache builder instance
        builder = sticky['builder'] = type(**kwargs)
        builder.Build()
        builder.AddLayers(builder.Layers)
        builder.Render()
        builder.Finalize()


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
        Analysis : dict
        Brep : Rhino.Geometry.Brep
        Breps : list<Rhino.Geometry.Brep
        CalabiYau : Builder
        Curves : list<Rhino.Geometry.NurbsCurve>
        Mesh : Rhino.Geometry.Mesh
        Meshes : list<Rhino.Geometry.Mesh>
        Phase : list
        Points : Rhino.Collections.Point3dList
        PointGrid : list
        Surface : Rhino.Geometry.NurbsSurface
        Surfaces : list<Rhino.Geometry.NurbsSurface>
    '''
    __slots__ = [
        'Analysis',
        'Brep', 'Breps',
        'CalabiYau',
        'Curves'
        'Mesh', 'Meshes',
        'Phase',
        'Points',
        'PointGrid',
        'Surface', 'Surfaces'
    ]

    def __init__(self, cy, phase):
        self.CalabiYau = cy
        self.Phase = phase
        self.Analysis = {}
        self.Points = Point3dList()
        self.Meshes = {}
        self.Surfaces = {}
        self.Breps = {}
        self.PointGrid = {}

        for (group, divisions) in __conf__.Div['m'].iteritems():
            self.Meshes[group] = {}
            for div in divisions:
                self.Meshes[group][div] = Mesh()

        for div in __conf__.Div['s'].keys():
            self.Surfaces[div] = []
            self.Breps[div] = []
            self.PointGrid[div] = []


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
        Layers : list<string>
        ndigits : int
            Rounding
        U : int
        V : int
        Degree : int
        DegreeU : int
        DegreeV : int
        CountU : int
        CountV : int
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
        Analysis : dict
        Rendered : dict
            Store Rhino object ids by object type.
        BoundingBox : list
        Points : list<Rhino.Geometry.Point3d>
        Point : Rhino.Geometry.Point3d
        PointCount : int
            Cumulative position within `Plot3D` nested loop --
            equiv to `len(self.Points)`
        Patches : list<Patch>
        Patch : Patch
        PatchCount : int
        IsoCurveDensity : int
        __palette__ : list<list<System.Drawing.Color>>
    '''
    __slots__ = ['n', 'Alpha', 'Step', 'Scale', 'Offset',
                 'ndigits',
                 'U', 'V',
                 'Degree', 'DegreeU', 'DegreeV',
                 'CountU', 'CountV',
                 'MinU', 'MidU', 'MaxU', 'StepU',
                 'MinV', 'MidV', 'MaxV', 'StepV',
                 'RngK', 'RngU', 'RngV',
                 'Analysis',
                 'Rendered',
                 'BoundingBox',
                 'Points', 'Point', 'PointCount',
                 'Patches', 'Patch', 'PatchCount',
                 'IsoCurveDensity',
                 '__palette__']

    def __init__(self, n=1, deg=1.0, density=2, scale=1, offset=(0, 0), **kwargs):
        '''
        Parameters:
            n : int
            deg : float
            scale : int
            offset : int
        '''
        self.n = n
        self.Alpha = deg * pi
        self.Scale = scale
        self.Offset = offset

        self.Layers = [
            'BoundingBox',
            'Camera'
        ]

        # Floating point precision.
        # Increase when `self.U` and/or `self.V` increases
        self.ndigits = 5

        # Note:
        #   `U` -- "xi" must be odd to guarantee passage through fixed points at
        #   (theta, xi) = (0, 0) and (theta, xi) = (pi / 2, 0)
        #
        #   Performance reduced if > 55
        # See:
        #   [Table 1](https://www.cs.indiana.edu/~hansona/papers/CP2-94.pdf)
        self.V = self.U = __conf__.GetNormalisedDensity(density)
        self.Degree = self.DegreeV = self.DegreeU = 3

        # Note: Polysurface created if U and V degrees differ.
        self.CountV = self.CountU = 0

        # xi
        self.MinU = -1
        self.MaxU = 1
        self.MidU = (self.MinU + self.MaxU) / 2.0  # 0
        # deduct 1 to accomodate `rs.frange` zero offset
        self.StepU = fabs(self.MaxU - self.MinU) / (self.U - 1.0)

        # theta as radians
        self.MinV = 0
        self.MaxV = pi / 2.0
        self.MidV = (self.MinV + self.MaxV) / 2.0  # pi / 4
        # deduct 1 to accomodate `rs.frange` zero offset
        self.StepV = fabs(self.MaxV - self.MinV) / (self.V - 1.0)

        self.RngK = rs.frange(0, n - 1, 1)
        self.RngU = rs.frange(self.MinU, self.MaxU, self.StepU)
        self.RngV = rs.frange(self.MinV, self.MaxV, self.StepV)

        self.IsoCurveDensity = 2

        self.Points = Point3dList()
        self.Point = None
        self.PointCount = 0

        self.Patches = []
        self.Patch = None
        self.PatchCount = 0

        self.__palette__ = util.Palette()

        self.Analysis = PointAnalysis
        self.Analysis.update({
            'docCentre': Point3d(0, 0, 0),
            '15': round(pi / 12, self.ndigits),
            '30': round(pi / 6, self.ndigits),
            '45': round(pi / 4, self.ndigits),
            '60': round(pi / 3, self.ndigits),
            '75': round(pi / 2.4, self.ndigits),
            '90': round(pi / 2, self.ndigits),
            'U/2': int(round(self.U / 2.0)),
            'V/2': int(round(self.V / 2.0)),
            'midU': round(self.MidU, self.ndigits),
            'midV': round(self.MidV, self.ndigits),
            'midRngU': len(self.RngU) / 2,
            'midRngV': len(self.RngV) / 2,
            'g': Genus(self.n),
            'chi': EulerCharacteristic(self.n)
        })

        self.Rendered = {
            'c': {},  # Rhino.Geometry.NurbsCurve
            'i': {'U': [], 'V': []},  # Rhino.Geometry.NurbsCurve [IsoCurve]
            'm': {},  # Rhino.Geometry.Mesh
            'p': [],  # Rhino.Geometry.Point3d
            's': {},  # Rhino.Geometry.NurbsSurface
            'S': {},  # Rhino.Geometry.Brep [PolySurface]
            'x': {}  # Rhino.Geometry.NurbsCurve [Intersection]
        }

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
            'a.on': [self.IncrementCountU],
            'a.in': [],
            'b.on': [self.BuildPoint, self.IncrementCountV],
            'b.in': [],
            'b.out': [],
            'a.out': [self.ResetCountV],
            'k2.out': [],
            'k1.out': []
        }

    def Build(self):
        '''
        Iterates `self.n ** 2` "phases" plotting the topology of the
        "Fermat surface" of degree `n`.
        There are `self.n ** 2` `Patch`es per surface.

        Functions registered with 'on', 'in', 'out' events will be
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

    def ResetCountU(self, *args):
        self.CountU = 0

    def ResetCountV(self, *args):
        self.CountV = 0

    def IncrementCountV(self, *args):
        self.CountV += 1

    def IncrementCountU(self, *args):
        self.CountU += 1

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

    def CompareDistance(self, *args):
        def fromReference(point):
            projection = self.Analysis['refSphere'].ClosestPoint(point, self.Analysis['radius'])

            return point.DistanceTo(projection[1])

        def fromCentre(point):
            return point.DistanceTo(self.Analysis['centre'])

        def fromMaxX(point):
            return point.DistanceTo(self.Analysis['maxX'])

        def fromMaxY(point):
            return point.DistanceTo(self.Analysis['maxY'])

        def fromMaxZ(point):
            return point.DistanceTo(self.Analysis['maxZ'])

        def GetDistance(val, func):
            result, parameter = val.ClosestPoint(self.Analysis['centre'])
            point = val.PointAt(parameter)  # val.PointAtStart

            return func(point)

        a, b = [GetDistance(val, fromCentre) for val in args]

        if a > b:
            return -1
        elif a == b:
            return 0
        elif a < b:
            return 1

    def BuildBoundingBox(self, objects):
        self.BoundingBox = rs.BoundingBox(objects)

        for i, point in enumerate(self.BoundingBox):
            # id = doc.Objects.AddTextDot(str(i), p)
            id = doc.Objects.AddPoint(point)
            rs.ObjectLayer(id, 'BoundingBox')

        return self.BoundingBox

    @staticmethod
    def BoxAnalysis(points):
        bx = Brep.CreateFromBox(points)

        Geometry.AreaMassProperties.Compute(bx)
        Geometry.VolumeMassProperties.Compute(bx)

    @staticmethod
    def SetAxonometricCameraProjection(bx):  # Isometric
        ln = rs.AddLine(bx[4], bx[2])
        rs.ObjectLayer(ln, 'Camera')
        rs.MoveObject(ln, bx[4] - bx[2])
        ln = rs.coerceline(ln)

        rs.ViewProjection('Perspective', 1)
        rs.ViewCameraTarget('Perspective', ln.From, ln.To)
        rs.ZoomBoundingBox(bx, all=True)
        rs.AddNamedView('Base', 'Perspective')

        for layer in ('Camera', 'BoundingBox'):
            rs.LayerVisible(layer, False)
            rs.LayerLocked(layer, True)

    @staticmethod
    def ClosestPoint(srf, point, maxDistance=0.1):
        '''
        If maximumDistance > 0, then only points whose distance is
        <= maximumDistance will be returned.
        http://developer.rhino3d.com/api/RhinoCommon/html/M_Rhino_Geometry_Brep_ClosestPoint_1.htm
        '''
        brep = Brep.TryConvertBrep(srf)
        _ = brep.ClosestPoint(point, maxDistance)

        return _[0], (_[3], _[4])

    @staticmethod
    def BuildReferenceSphere(centre=(0, 0, 0), radius=150):
        center = rs.coerce3dpoint(centre)

        return Sphere(center, radius).ToBrep()

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

    @staticmethod
    def AddLayers(layers):
        for i in range(1, 5 + 1):
            layer = ' '.join(('Layer', '0' + str(i)))
            if rs.IsLayer(layer):
                rs.DeleteLayer(layer)

        for layer in layers:
            if not rs.IsLayer(layer):
                layer = rs.AddLayer(layer)
                rs.LayerPrintColor(layer, Color.Black)
                rs.LayerPrintWidth(layer, 0.4)  # mm
                # rs.LayerVisible(layer, False)

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
        Parameters:
            cb : function
            group : string
        '''
        ids = []

        for k1, phase in enumerate(util.chunk(self.Patches, self.n)):
            parent = util.layer(group, k1)

            for k2, patch in enumerate(phase):
                cb(
                    phase,
                    patch,
                    (util.layer(parent, k2), self.Colour(self.n, k1, k2)),
                    ids
                )

        doc.Views.Redraw()

        return ids


class PointCloudBuilder(Builder):
    __slots__ = Builder.__slots__

    def __init__(self, **kwargs):
        Builder.__init__(self, **kwargs)

        self.Layers.append('Points')

    def Render(self, *args):
        parent = rs.AddLayer('Points')

        def cb(phase, patch, layer, ids):
            layer = rs.AddLayer(*layer)

            for point in patch.Points:
                id = doc.Objects.AddPoint(point)
                ids.append(id)
                rs.ObjectLayer(id, layer)
                self.Rendered['p'].append(id)

        Builder.Render(self, cb, parent, *args)


class MeshBuilder(Builder):
    __slots__ = Builder.__slots__ + ['MeshCount', 'Meshes']

    def __init__(self, **kwargs):
        Builder.__init__(self, **kwargs)

        self.Layers.append('Meshes')
        self.MeshCount = 0
        self.Meshes = {}

        for (group, divisions) in __conf__.Div['m'].iteritems():
            self.Rendered['m'][group] = []
            self.Meshes[group] = {}

    def __listeners__(self):
        listeners = Builder.__listeners__(self)
        listeners['k2.on'].append(self.AddMesh)
        listeners['b.on'].append(self.IncrementMeshCount)
        listeners['b.in'].append(self.BuildMesh)
        listeners['k2.out'].append(self.WeldMesh)

        return listeners

    def AddMesh(self, *args):
        # k1, k2 = args

        for (group, divisions) in __conf__.Div['m'].iteritems():
            for div in divisions:
                self.Meshes[group][div] = Mesh()

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
                mesh = self.Meshes[1]['M_0'] = Mesh()
                self.BuildFaces(mesh, *args)
                self.Patch.Meshes[1]['M_0'].Append(mesh)
            else:
                mesh = self.Meshes[1]['M_1'] = Mesh()
                self.BuildFaces(mesh, *args)
                self.Patch.Meshes[1]['M_1'].Append(mesh)

    def WeldMesh(self, *args):
        for (group, divisions) in __conf__.Div['m'].iteritems():
            for div in divisions:
                self.Patch.Meshes[group][div].Weld(pi)

    def Render(self, *args):
        parent = rs.AddLayer('Meshes')

        def cb(phase, patch, layer, ids):
            layer = rs.AddLayer(*layer)

            for i, (group, divisions) in enumerate(__conf__.Div['m'].iteritems()):
                for div in divisions:
                    id = doc.Objects.AddMesh(patch.Meshes[group][div])
                    self.__rendered__(id)
                    ids.append(id)
                    rs.ObjectLayer(id, layer)
                    self.Rendered['m'][group].append(id)

        Builder.Render(self, cb, parent, *args)


class CurveBuilder(Builder):
    '''
    Note:
        IsoCurves MUST be interpolated upon the corresponding NurbsSurface.
        DO NOT attempt to generate IsoCurves from points alone;
        deviation from Surface is NOT within `doc.AbsoluteTolerance`
        necessary for precise `Make2d` rendering.
    See:
        [#14](https://bitbucket.org/kunst_dev/snippets/issues/14/wireframe#comment-40891348)
        `SurfaceBuilder.BuildIsoCurves.InterpCrvOnSrfThroughPoints`
    '''
    __slots__ = Builder.__slots__ + [
        'CurveCombinations',
        'Curves',
        'Outer'
    ]

    for (group, subGroups) in __conf__.Div['c'].iteritems():
        for (subGroup, divisions) in subGroups.iteritems():
            __slots__.append(subGroup)

    def __init__(self, **kwargs):
        Builder.__init__(self, **kwargs)

        self.__groups__ = __conf__.Div['c'].keys()

        self.Layers.extend([
            'Border::All',
            'Border::Outer',
            'Curves',
            'Intersect::Curves',
            'Intersect::Points'
        ])
        self.Curves = CurveList()
        self.CurveCombinations = None
        self.Outer = CurveList()

        for (group, subGroups) in __conf__.Div['c'].iteritems():
            self.Curves[group] = {}

            for (subGroup, divisions) in subGroups.iteritems():
                self.Curves[group][subGroup] = {}

                setattr(self, subGroup, CurveList())

    def __listeners__(self):
        listeners = Builder.__listeners__(self)
        listeners['k2.on'].append(self.AddCurves)
        listeners['b.in'].extend([
            self.PlotRails,
            self.PlotXSections,
            self.PlotIsoCurves
        ])
        listeners['k2.out'].extend([
            self.BuildCurves,
            self.ResetCountU
        ])

        return listeners

    def AddCurves(self, *args):
        for (group, subGroups) in __conf__.Div['c'].iteritems():
            self.Patch.Curves[group] = {}

            for (subGroup, divisions) in subGroups.iteritems():
                self.Patch.Curves[group][subGroup] = {}

                for div in divisions:
                    self.Curves[group][subGroup][div] = Point3dList()

    def PlotRails(self, *args):
        '''
        [#10](https://bitbucket.org/kunst_dev/snippets/issues/10/curve-generation)
        '''
        # k1, k2, a, b = args

        for group in self.__groups__:
            subGroup = self.Curves[group]['R']

            if self.Analysis['xi == minU']:
                subGroup['R_2'].Add(self.Point)
            elif self.Analysis['xi == midU']:
                subGroup['R_1'].Add(self.Point)
            elif self.Analysis['xi == maxU']:
                subGroup['R_0'].Add(self.Point)

    def PlotXSections(self, *args):
        # k1, k2, a, b = args

        for group in self.__groups__:
            subGroup = self.Curves[group]['X']

            if self.Analysis['theta == 0']:
                if self.Analysis['xi <= midU']:
                    subGroup['X_9'].Add(self.Point)
                if self.Analysis['xi >= midU']:
                    subGroup['X_8'].Add(self.Point)
            elif self.Analysis['theta == 30']:
                if self.Analysis['xi <= midU']:
                    subGroup['X_7'].Add(self.Point)
                if self.Analysis['xi >= midU']:
                    subGroup['X_6'].Add(self.Point)
            elif self.Analysis['theta == 45']:
                if self.Analysis['xi <= midU']:
                    subGroup['X_5'].Add(self.Point)
                if self.Analysis['xi >= midU']:
                    subGroup['X_4'].Add(self.Point)
            elif self.Analysis['theta == 60']:
                if self.Analysis['xi <= midU']:
                    subGroup['X_3'].Add(self.Point)
                if self.Analysis['xi >= midU']:
                    subGroup['X_2'].Add(self.Point)
            elif self.Analysis['theta == 90']:
                if self.Analysis['xi <= midU']:
                    subGroup['X_1'].Add(self.Point)
                if self.Analysis['xi >= midU']:
                    subGroup['X_0'].Add(self.Point)

    def PlotIsoCurves(self, *args):
        # k1, k2, a, b = args

        for group in self.__groups__:
            group = self.Curves[group]

            for direction in ('U', 'V'):
                if group.has_key(direction):
                    subGroup = self.Curves[group][direction]
                    count = getattr(self, 'Count' + direction) - 1
                    subGroup[direction + '_' + str(count)].Add(self.Point)

    def BuildCurves(self, *args):
        def cache(curve, group, subGroup, div):
            curve = self.BuildInterpolatedCurve(curve, self.Degree)

            arr[div] = self.Patch.Curves[group][subGroup][div] = curve
            getattr(self, subGroup).Add(curve)

            # See:
            #   [#14](https://bitbucket.org/kunst_dev/snippets/issues/14#comment-40891348)
            if subGroup == 'R' and i != 1:
                self.Outer.Add(curve)

        for (group, subGroup) in __conf__.Div['c'].iteritems():
            for (subGroup, divisions) in subGroup.iteritems():
                subGroup = self.Curves[group][subGroup]

                for i, div in enumerate(divisions):
                    points = subGroup[div]

                    if subGroup == 'V':  # Ensure sharp kink
                        count = int(self.Analysis['V/2'] - 1)

                        for i, curve in enumerate((
                            points.GetRange(0, count),
                            points.GetRange(count - 1, count)
                        )):
                            div = div + '_' + str(i)
                            __conf__.Div['c'][group][subGroup].append(div)
                            cache(curve, group, subGroup, div)
                    else:
                        cache(points, group, subGroup, div)

    def Render(self, *args):
        for k1, phase in enumerate(util.chunk(self.Patches, self.n)):
            for k2, patch in enumerate(phase):
                for i, (group, subGroups) in __conf__.Div['c'].iteritems():
                    for (subGroup, divisions) in subGroups.iteritems():
                        parent = util.layer('Curves', subGroup, k1)
                        if not rs.isLayer(parent):
                            parent = rs.AddLayer(parent)
                            layer = util.layer(parent, k2)
                            if not rs.isLayer(layer):
                                colour = self.Colour(self.n, k1, k2)
                                layer = rs.AddLayer(util.layer(parent, k2), colour)

                        for div in divisions:
                            curve = patch.Curves[group][subGroup][div]
                            id = doc.Objects.AddCurve(curve)
                            self.__rendered__(id)
                            rs.ObjectLayer(id, layer)
                            self.Rendered['c'][group].append(id)

                            # self.FindCurveCentre(curve, '[' + str(k1) + ',' + str(k2) + ']')

    @staticmethod
    def DivideCurve(curve, div):
        '''
        `Curve.DivideByLength` varies according to curvature
        unlike `Curve.DivideEquidistant`

        Example:
            for curve in self.Outer:  # Curve.JoinCurves(self.Outer):
                self.DivideCurve(curve, 20)

        Parameters:
            count : int
            length : float
                n * UnitSystem between points along
        '''
        # points = curve.DivideEquidistant(div)

        # result = curve.DivideByLength(div, True)
        # points = [curve.PointAt(t) for t in result]

        result = curve.DivideByCount(div, True)
        points = [curve.PointAt(t) for t in result]

        return points

    def CombineCurves(self):
        '''
        Returns unique combinations of keys in self.Curves[group]
        '''
        for (group, subGroups) in __conf__.Div['c'].iteritems():
            if not self.CurveCombinations.has_key(group):
                self.CurveCombinations[group]
                for (subGroup, divisions) in subGroups.iteritems():
                    self.CurveCombinations[group] = combinations(divisions, 2)

        return self.CurveCombinations

    def IntersectCurves(self):
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

        for (group, subGroups) in __conf__.Div['c'].iteritems():
            for (subGroup, divisions) in subGroups.iteritems():
                # "self-intersections"
                for curve in self.Curves[group][subGroup].itervalues():
                    result = Intersect.Intersection.CurveSelf(curve, 0.1)
                    HandleIntersectionEvents(result)

                # "intersection"
                for (a, b) in self.CurveCombinations[group]:
                    result = Intersect.Intersection.CurveCurve(a, b, 0.1, 1.0)
                    HandleIntersectionEvents(result)

        rs.UnitAbsoluteTolerance(tolerance, True)  # restore tolerance


class SurfaceBuilder(CurveBuilder):
    pass
    # '''
    # Build quadrilateral surfaces.
    # See [Example](https://bitbucket.org/snippets/kunst_dev/X894E8)
    # '''
    # __slots__ = CurveBuilder.__slots__ + [
    #     '__points__',
    #     'Breps',
    #     'PointGrid',
    #     'PolySurfaces',
    #     'SurfaceCombinations',
    #     'Surfaces'
    # ]
    #
    # def __init__(self, **kwargs):
    #     CurveBuilder.__init__(self, **kwargs)
    #
    #     self.Layers.extend([
    #         'IsoCurves::U',
    #         'IsoCurves::V',
    #         'IsoCurves',
    #         'PolySurfaces',
    #         'Surfaces'
    #     ])
    #
    #     self.__groups__ = __conf__.Div['s'].keys()
    #
    #     self.Surfaces = {}
    #     self.Breps = {}
    #     self.PointGrid = {}
    #     self.SurfaceCombinations = {}
    #     self.PolySurfaces = {}
    #
    #     for (group, divisions) in __conf__.Div['s'].iteritems():
    #         self.Rendered['s'][group] = []
    #
    #         self.Surfaces[group] = {}
    #         self.Breps[group] = {}
    #         self.PointGrid[group] = {}
    #         self.SurfaceCombinations[group] = {}
    #
    #         for div in divisions:
    #             self.Surfaces[group][div] = []
    #             self.Breps[group][div] = []
    #             self.PointGrid[group][div] = []
    #             self.SurfaceCombinations[group][div] = None
    #
    #     for (group, divisions) in __conf__.Div['S'].iteritems():
    #         self.Rendered['S'][group] = []
    #
    #         self.PolySurfaces[group] = {}
    #
    #         for div in divisions:
    #             self.PolySurfaces[group][div] = None
    #
    # def __listeners__(self):
    #     listeners = CurveBuilder.__listeners__(self)
    #     listeners['k2.on'].append(self.AddSurfaces)
    #     listeners['b.in'].append(self.PlotSurface)
    #     listeners['k2.out'].extend([self.BuildSurface, self.JoinSurfaces])
    #
    #     return listeners
    #
    # def AddSurfaces(self, *args):
    #     '''
    #     Reset parameter counts and add a point repository per division
    #     '''
    #     if 0 in self.__groups__:
    #         for (group, subGroups) in __conf__.Div['s'][0]
    #         setattr(self, 'C', Point3dList())
    #
    #     if 1 in self.__groups__:
    #         for div in ('A', 'B'):
    #             setattr(self, div, Point3dList())
    #
    #     if 2 in self.__groups__:
    #         for div in __conf__.Div2['s']:
    #             setattr(self, div, Point3dList())
    #         for div in __conf__.Div2['U']:
    #             setattr(self, div, 0)
    #         for div in __conf__.Div2['V']:
    #             setattr(self, div, 0)
    #
    # def AddSurfaceSubdivision(self, *args):
    #     '''
    #     Example:
    #         Make further U divisions as below:
    #         ```
    #         xi == self.RngU[self.Analysis['midRngU']]
    #         self.Analysis['midU']
    #         self.OffsetU(-3.0)
    #         self.OffsetU(3.0)
    #         ```
    #     '''
    #     k1, k2, a, b = args
    #
    #     if self.Analysis['theta == 90']:
    #         if self.Analysis['midU']:
    #             self.BuildSurface(*args)  # Finalise current subdivision
    #             self.AddSurface(*args)  # Begin next subdivision
    #             self.__points__ = Point3dList(self.Points[-self.Analysis['U/2']:])
    #             self.IncrementCountU()
    #
    # def PlotSurface(self, *args):
    #     k1, k2, a, b = args
    #
    #     if 0 in self.__groups__:
    #         self.C.Add(self.Point)
    #
    #     if 1 in self.__groups__:
    #         if self.Analysis['xi <= midU']:
    #             self.A.Add(self.Point)
    #         if self.Analysis['xi >= midU']:
    #             self.B.Add(self.Point)
    #
    #     if 2 in self.__groups__:
    #         if self.Analysis['theta <= 30']:
    #             if self.Analysis['xi == minU']:
    #                 self.V0_0 += 1
    #             elif self.Analysis['xi == midU']:
    #                 self.V0_1 += 1
    #
    #             if self.Analysis['xi <= midU']:
    #                 self.S0_0.Add(self.Point)
    #             if self.Analysis['xi >= midU']:
    #                 self.S0_1.Add(self.Point)
    #
    #         if self.Analysis['theta >= 30'] and self.Analysis['theta <= 45']:
    #             if self.Analysis['xi == minU']:
    #                 self.V30_0 += 1
    #             elif self.Analysis['xi == midU']:
    #                 self.V30_1 += 1
    #
    #             if self.Analysis['xi <= midU']:
    #                 self.S30_0.Add(self.Point)
    #             if self.Analysis['xi >= midU']:
    #                 self.S30_1.Add(self.Point)
    #
    #         if self.Analysis['theta >= 45'] and self.Analysis['theta <= 60']:
    #             if self.Analysis['xi == minU']:
    #                 self.V45_0 += 1
    #             elif self.Analysis['xi == midU']:
    #                 self.V45_1 += 1
    #
    #             if self.Analysis['xi <= midU']:
    #                 self.S45_0.Add(self.Point)
    #             if self.Analysis['xi >= midU']:
    #                 self.S45_1.Add(self.Point)
    #
    #         if self.Analysis['theta >= 60'] and self.Analysis['theta <= 90']:
    #             if self.Analysis['xi == minU']:
    #                 self.V60_0 += 1
    #             elif self.Analysis['xi == midU']:
    #                 self.V60_1 += 1
    #
    #             if self.Analysis['xi <= midU']:
    #                 self.S60_0.Add(self.Point)
    #             if self.Analysis['xi >= midU']:
    #                 self.S60_1.Add(self.Point)
    #
    # def BuildSurface(self, *args):
    #     '''
    #     TODO Add `Weight` to `self.Patch.Analysis['centre']` control point
    #
    #     NurbsSurface.CreateThroughPoints will raise "Invalid U and V counts" if
    #     `Point3dList != self.CountU * self.CountV`
    #
    #     ```
    #         cp = srf.Points.GetControlPoint(0, self.Analysis['V/2'])
    #         cp.Weight = 1000
    #     ```
    #     '''
    #     def cache(srf, key):
    #         self.Surfaces[key].append(srf)
    #         self.Patch.Surfaces[key].append(srf)
    #
    #         brep = Brep.TryConvertBrep(srf)
    #         self.Breps[key].append(brep)
    #         self.Patch.Breps[key].append(brep)
    #
    #     def PointGrid(points, CountU, CountV):
    #         count = len(points)
    #
    #         U = [[] for n in range(CountV)]
    #         V = []  # [] for n in range(CountU)
    #
    #         for n in range(0, count, CountV):
    #             arr = points.GetRange(n, CountV)
    #             V.append(arr)
    #
    #         for n in range(CountV):
    #             for arr in V:
    #                 U[n].append(arr[n])
    #
    #         return U, V
    #
    #     groups = __conf__.Div['s'].keys()
    #
    #     if 0 in self.__groups__:
    #         points = getattr(self, 'C')
    #
    #         if points.Count > 0:
    #             CountU = self.U
    #             CountV = self.V
    #
    #             pointGrid = {}
    #             self.Patch.PointGrid[0].append(pointGrid)
    #             for e in zip(('U', 'V'), PointGrid(points, CountU, CountV)):
    #                 pointGrid[e[0]] = e[1]
    #
    #             srf = NurbsSurface.CreateThroughPoints(
    #                 points,
    #                 CountU,
    #                 CountV,
    #                 self.DegreeU,
    #                 self.DegreeV,
    #                 False,
    #                 False)
    #
    #             cache(srf, 0)
    #
    #     if 1 in self.__groups__:
    #         for div in __conf__.Div['s'][1]['S']:
    #             points = getattr(self, char)
    #
    #             if points.Count > 0:
    #                 CountU = self.Analysis['U/2']
    #                 CountV = self.V
    #
    #                 pointGrid = {}
    #                 self.Patch.PointGrid[1].append(pointGrid)
    #                 for e in zip(('U', 'V'), PointGrid(points, CountU, CountV)):
    #                     pointGrid[e[0]] = e[1]
    #
    #                 srf = NurbsSurface.CreateThroughPoints(
    #                     points,
    #                     CountU,
    #                     CountV,
    #                     self.DegreeU,
    #                     self.DegreeV,
    #                     False,
    #                     False)
    #
    #                 # Build IsoCurves from PointGrid. Do this for 'Div1' surfaces only.
    #                 # Make2d seems to perform better when given fewer objects properly joined.
    #                 for i, direction in enumerate(('U', 'V')):
    #                     isoCurves, seams = self.BuildIsoCurves(srf, pointGrid, direction, 10)
    #
    #                     for collection in (self.Patch.IsoCurves, self.IsoCurves):
    #                         collection[direction].AddRange(isoCurves)
    #
    #                 cache(srf, 1)
    #
    #     if 2 in self.__groups__:
    #         for i in range(0, 2, 1):
    #             for char in range(0, 90 + 15, 15):
    #                 points = getattr(self, 'S' + str(char) + '_' + str(i))
    #
    #                 if points.Count > 0:
    #                     CountU = self.Analysis['U/2']
    #                     CountV = getattr(self, 'V' + str(char) + '_' + str(i))
    #
    #                     pointGrid = {}
    #                     self.Patch.PointGrid['Div2'].append(pointGrid)
    #                     for e in zip(('U', 'V'), PointGrid(points, CountU, CountV)):
    #                         pointGrid[e[0]] = e[1]
    #
    #                     srf = NurbsSurface.CreateThroughPoints(
    #                         points,
    #                         CountU,
    #                         CountV,
    #                         self.DegreeU,
    #                         self.DegreeV,
    #                         False,
    #                         False)
    #
    #                     cache(srf, 2)
    #
    # def JoinSurfaces(self, *args):
    #     '''
    #     TODO Join Patch subdivisions
    #     Increase `doc.ModelAbsoluteTolerance` to maximise polysurface inclusion
    #     '''
    #     pass
    #
    #     tolerance = 0.1
    #     result = []
    #
    #     for i, e in enumerate(__conf__.Div):
    #         result.append(Brep.JoinBreps(self.Patch.Breps[e], tolerance))
    #         # for srf in result:
    #         #     id = doc.Objects.AddBrep(srf)
    #         #     self.__rendered__(id)
    #         #     rs.ObjectLayer(id, 'PolySurfaces')
    #
    #     return result
    #
    # def Render(self, *args):
    #     def cb(phase, patch, layer, ids):
    #         layer, colour = layer
    #
    #         for i, e in enumerate(__conf__.Div):
    #             subLayer = rs.AddLayer(util.layer('Surfaces', e, *patch.Phase), colour)
    #
    #             for srf in patch.Surfaces[e]:
    #                 id = doc.Objects.AddSurface(srf)
    #                 self.__rendered__(id)
    #                 ids.append(id)
    #                 rs.ObjectLayer(id, subLayer)
    #                 self.Rendered['s'][e].append(id)
    #
    #     Builder.Render(self, cb, 'Surfaces', *args)
    #     CurveBuilder.Render(self, *args)
    #
    # def Finalize(self):
    #     # Redundant
    #     #   * `self.ConvertToBeziers()`
    #     #   * `self.BuildSilhouette()`
    #
    #     self.BuildBoundingBox(self.Surfaces[1])  # self.PolySurfaces['Div1']
    #     self.SetAxonometricCameraProjection(self.BoundingBox)
    #
    #     self.Dimensions()
    #
    #     self.CombineCurves()
    #     self.CombineSurfaces()
    #     self.BuildPolySurface()
    #     self.BuildBorders()
    #     self.BuildWireframe()
    #     # self.IntersectCurves()
    #     # Curves, Points = self.IntersectSurfaces()
    #     # self.SplitAtIntersection()
    #
    #     doc.Views.Redraw()
    #
    # def CombineSurfaces(self):
    #     '''
    #     Returns unique combinations of keys in self.Surfaces[group]
    #     '''
    #     for (group, divisions) in __conf__.Div['s'].iteritems():
    #         if not self.SurfaceCombinations.has_key(group):
    #             self.SurfaceCombinations[group] = combinations(divisions, 2)
    #
    #     return self.SurfaceCombinations
    #
    # @staticmethod
    # def AnalyseSurface(srf):
    #     '''
    #     Attempts to step through paramater space by `Rhino.Geometry.NurbsSurface.SpanCount`.
    #
    #     Note:
    #         Do not attempt to divide NURBS parameter space to obtain length.
    #     See:
    #         https://ieatbugsforbreakfast.wordpress.com/2013/09/27/curve-parameter-space/
    #     '''
    #     _ = {}
    #     _['U'] = srf.SpanCount(0)  # srf.Points.CountU
    #     _['V'] = srf.SpanCount(1)  # srf.Points.CountV
    #     _['minU'], _['maxU'] = srf.Domain(1)
    #     _['minV'], _['maxV'] = srf.Domain(0)
    #     _['stepU'] = fabs(_['maxU'] - _['minU']) / float(_['U'] - 1)
    #     _['stepV'] = fabs(_['maxV'] - _['minV']) / float(_['V'] - 1)
    #
    #     # srf.Evaluate()
    #     # srf.CurvatureAt()
    #     # srf.GetSurfaceSize()
    #     # srf.FrameAt()
    #     # srf.OrderU
    #     # srf.OrderV
    #     #
    #     # brep.SolidOrientation()
    #     # brep.Loops()
    #     # brep.Curves2D()
    #
    #     return _
    #
    # def Dimensions(self):
    #     '''
    #     Calculate form bounds and reference points
    #     '''
    #     _ = self.Analysis
    #
    #     bx = self.BoundingBox
    #
    #     origin = bx[0]
    #
    #     _['offset'] = (origin - _['docCentre']).Length
    #
    #     _['distance'] = [(origin - bx[i]).Length for i in (1, 3, 4)]
    #     _['diagonal'] = [(bx[a] - bx[b]).Length for (a, b) in combinations((1, 3, 4), 2)]
    #
    #     _['centre'] = Point3d(*[origin[i] + (dist / 2.0) for i, dist in enumerate(_['distance'])])
    #
    #     dx, dy, dz = _['distance']
    #     cx, cy, cz = _['centre']
    #     xy, xz, yz = _['diagonal']
    #
    #     _['minX'] = Point3d(cx - (dx / 2.0), cy, cz)
    #     _['maxX'] = Point3d(cx + (dx / 2.0), cy, cz)
    #
    #     _['minY'] = Point3d(cx, cy - (dy / 2.0), cz)
    #     _['maxY'] = Point3d(cx, cy + (dy / 2.0), cz)
    #
    #     _['minZ'] = Point3d(cx, cy, cz - (dz / 2.0))
    #     _['maxZ'] = Point3d(cx, cy, cz + (dz / 2.0))
    #
    #     _['diameter'] = max(_['diagonal'])
    #     _['radius'] = _['diameter'] / 2.0
    #
    #     _['refSphere'] = self.BuildReferenceSphere(_['centre'], _['radius'])
    #
    #     return self.Analysis
    #
    # def BuildPolySurface(self):
    #     tolerance = 0.1
    #
    #     for i, e in enumerate(__conf__.PolySurfaces):
    #         layer = rs.AddLayer(util.layer('PolySurfaces', e))
    #         result = Brep.JoinBreps(self.Breps[e], tolerance)
    #
    #         for srf in result:
    #             id = doc.Objects.AddBrep(srf)
    #             self.__rendered__(id)
    #             rs.ObjectLayer(id, layer)
    #             self.Rendered['S'][e].append(id)
    #
    #         self.PolySurfaces[e], = result
    #
    #     return self.PolySurfaces
    #
    # def IntersectSurfaces(self):
    #     tolerance = doc.ModelAbsoluteTolerance
    #
    #     Curves = CurveList()
    #     Points = Point3dList()
    #
    #     Edges = [(e.PointAtStart, e.PointAtEnd) for e in self.Curves]
    #
    #     # Use "smallest" divisions to demarcate patch self-intersection(s)
    #     for (a, b) in self.SurfaceCombinations[2]:
    #         a = self.Breps[2][a]
    #         b = self.Breps[2][b]
    #
    #         result, curves, points = Intersect.Intersection.BrepBrep(a, b, tolerance)
    #
    #         for point in points:
    #             pass
    #
    #             Points.Add(point)
    #             id = doc.Objects.AddPoint(point)
    #             self.__rendered__(id)
    #             rs.ObjectLayer(id, 'Intersect::Points')
    #
    #         for curve in curves:
    #             C1 = curve.PointAtStart
    #             C2 = curve.PointAtEnd
    #
    #             for edge in Edges:
    #                 """
    #                 TODO TRY IsAtSeam
    #                 http://developer.rhino3d.com/api/RhinoCommonWin/html/M_Rhino_Geometry_Surface_IsAtSeam.htm
    #                 """
    #                 E1, E2 = edge
    #                 match = C1.EpsilonEquals(E1, 0.1) and C2.EpsilonEquals(E2, 0.1) or C1.EpsilonEquals(E2, 0.1) and C2.EpsilonEquals(E1, 0.1)  # reverse
    #
    #                 if not match:
    #                     Curves.Add(curve)
    #                     id = doc.Objects.AddCurve(curve)
    #                     self.__rendered__(id)
    #                     rs.ObjectLayer(id, 'Intersect::Curves')
    #                     self.Rendered['x'].append(id)
    #
    #     return Curves, Points
    #
    # def BuildBorders(self):
    #     # for curve in self.Curves:
    #     #     id = doc.Objects.AddCurve(curve)
    #     #     self.__rendered__(id)
    #     #     rs.ObjectLayer(curve, 'Border::All')
    #
    #     for curve in Curve.JoinCurves(self.Outer):
    #         id = doc.Objects.AddCurve(curve)
    #         self.__rendered__(id)
    #         rs.ObjectLayer(id, 'Border::Outer')
    #
    # def BuildWireframe(self, join=True):
    #     for e in ('U', 'V'):
    #         if join:
    #             curves = sorted(
    #                 Curve.JoinCurves(self.IsoCurves[e], 0.1, False),
    #                 cmp=self.CompareDistance)
    #         else:
    #             curves = self.IsoCurves[e]
    #
    #         for curve in curves:  # [::self.IsoCurveDensity]
    #             id = doc.Objects.AddCurve(curve)
    #             self.__rendered__(id)
    #             rs.ObjectLayer(id, util.layer('IsoCurves', e))
    #             # Add id to self.Rendered['i'] to facilitate staged Make2d algorithm.
    #             self.Rendered['i'][e].append(id)
    #
    #     return self.Rendered['i']
    #
    # def BuildIsoCurves(self, srf, grid, direction, count=3):
    #     def InterCrvOnSrfThroughDivisions():
    #         '''
    #         FAIL `ExtractIsoCurve` produces discontinuous curves.
    #         FAIL Synch divisions to world coordinates, else divisions across sympathetic Outer curves will be misaligned.
    #         '''
    #         tolerance = doc.ModelAbsoluteTolerance
    #         points = grid[direction]
    #         curves = []
    #
    #         edge1 = srf.InterpolatedCurveOnSurface(points[0], 0.1)
    #         edge2 = srf.InterpolatedCurveOnSurface(points[-1], 0.1)
    #
    #         div1 = self.DivideCurve(edge1, div=count)
    #         div2 = self.DivideCurve(edge2, div=count)
    #
    #         for i in range(count + 1):
    #             points = (div1[i], div2[i])  # start, end
    #             curves.append(srf.InterpolatedCurveOnSurface(points, tolerance))
    #
    #         return curves
    #
    #     def InterpCrvOnSrfThroughPoints(srf, grid):
    #         '''
    #         Increase point samples for higher isocurve density
    #         '''
    #         def build(arr, direction):
    #             segments = CurveList()
    #
    #             for points in arr:
    #                 curve = srf.InterpolatedCurveOnSurface(points, 0.1)
    #                 segments.Add(curve)
    #
    #             return segments
    #
    #         isoCurves = CurveList()
    #         seams = CurveList()
    #         count = len(grid)
    #
    #         # Separate first and last; JoinCurves fails when duplicates overlap at surface seams
    #         # `CurveList.AddRange(CurveList.GetRange(1, count - 2))`
    #
    #         # All segments between first and last positions within patch
    #         for segment in build(grid[1:-1], direction):
    #             isoCurves.Add(segment)
    #
    #         # First and last segments
    #         for segment in build(grid[0::(count - 1)], direction):
    #             seams.Add(segment)
    #
    #         return isoCurves, seams
    #
    #     return InterpCrvOnSrfThroughPoints(srf, grid[direction])
    #
    # @staticmethod
    # def ExtractIsoCurve(srf, parameter, direction=0):
    #     isBrep = type(srf) is BrepFace
    #     U = []
    #     V = []
    #
    #     for i, args in enumerate((('U', 1), ('V', 0))):
    #         arr = eval(args[0])
    #
    #         if direction in (i, 2):
    #             if isBrep:
    #                 arr.extend(srf.TrimAwareIsoCurve(i, parameter[args[1]]))
    #             else:
    #                 arr.append(srf.IsoCurve(i, parameter[args[1]]))
    #
    #     return U, V
    #
    # def ConvertToBeziers():
    #     pass
    #
    #     layer = rs.AddLayer('Beziers')
    #     beziers = []
    #
    #     # for srf in self.Surfaces['Div2']:
    #     #     bezier = Rhino.ConvertSurfaceToBezier(srf, False)
    #     #     beziers.append(bezier)
    #     #     rs.ObjectLayer(bezier, layer)
    #
    #     # rs.ObjectsByType(rs.filter.polysurface, True)
    #     # rs.Command('ConvertToBeziers')
    #
    #     rs.LayerLocked(layer, True)
    #
    #     return beziers
    #
    # def SplitAtIntersection(self):
    #     pass
    #     # breps = a.Split(b, tolerance)
    #     #
    #     # if len(breps) > 0:
    #     #     rhobj = rs.coercerhinoobject(a, True)
    #     #     if rhobj:
    #     #         attr = rhobj.Attributes if rs.ContextIsRhino() else None
    #     #         result = []
    #     #
    #     #         for i in range(len(breps)):
    #     #             if i == 0:
    #     #                 doc.Objects.Replace(rhobj.Id, breps[i])
    #     #                 result.append(rhobj.Id)
    #     #             else:
    #     #                 result.append(doc.Objects.AddBrep(breps[i], attr))
    #     #     else:
    #     #         result = [doc.Objects.AddBrep(brep) for brep in breps]
    #
    # def BuildSilhouette():
    #     pass
    #
    #     rs.CurrentLayer('PolySurfaces')
    #     rs.Command('_Silhouette')
    #     for id in rs.ObjectsByType(rs.filter.curve, True):
    #         rs.ObjectLayer(id, 'Silhouette')
    #     rs.LayerLocked('Silhouette', True)


__builders__ = {
    1: PointCloudBuilder,
    2: MeshBuilder,
    3: CurveBuilder,
    4: SurfaceBuilder
}
