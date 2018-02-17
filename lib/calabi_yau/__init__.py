import os
from math import pi, fabs
import System.Guid
import System.Drawing
import System.Enum
from scriptcontext import doc
# from rhinoscriptsyntax import GetBoolean, GetInteger,
#   GetReal, AddObjectsToGroup, AddGroup, frange
import rhinoscriptsyntax as rs
import utility
import builder
import export
from export import fname
import layers
from events import EventHandler
import builder

reload(utility)
reload(builder)
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
            arr.append(Manifold(int(n), a, density, scale, (x, y), type))
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
        #     queue[out] = Manifold(int(n), a, density, scale, (0, 0), type)
        out = export.fname('3dm', os.path.join(dir, str(n)), 'CY', n, str(float(alpha)))
        queue[out] = Manifold(int(n), alpha, density, scale, (0, 0), type)

    return queue


def Run(*args):
    if rs.ContextIsRhino():  # rs.ContextIsGrasshopper()
        args = GetUserInput()

    Manifold(*args).Build()
    doc.Views.Redraw()


def Layers():
    layers.Build()
    doc.Views.Redraw()


class Manifold:
    '''
    Replaces Grasshopper workflow -- execute via `RunPythonScript`

    Algorithm based on [Andrew J. Hanson](https://www.cs.indiana.edu/~hansona/papers/CP2-94.pdf).

    See:
        * [Python Standard Library - math](https://docs.python.org/2/library/math.html)
        * [Python Standard Library - cmath](https://docs.python.org/2/library/cmath.html)
        * [](http://www.tanjiasi.com/surface-design/)
        * [](http://www.food4rhino.com/app/calabi-yau-manifold)

    Following Hanson's conventions for symbolic representation:
        * `U == a == xi`
        * `V == b == theta`

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
        Builder : class
    '''
    __slots__ = ['n', 'Alpha', 'Step', 'Scale', 'Offset',
                 'U', 'V',
                 'MinU', 'MaxU', 'StepU', 'CentreU',
                 'MinV', 'MaxV', 'StepV', 'CentreV',
                 'RngK', 'RngU', 'RngV']

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

        # NOTE `U` -- "xi" must be odd to guarantee passage through fixed points at
        # (theta, xi) = (0, 0) and (theta, xi) = (pi / 2, 0)
        # [Table 1](https://www.cs.indiana.edu/~hansona/papers/CP2-94.pdf)
        # Performance reduced if > 55
        self.U = 55  # 11, 21, 55, 107, 205 [110]
        self.V = 55

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

        if type == 5:
            # TODO
            # self.Builder = All
            pass
        elif type is None:
            raise Exception('Builder not specified')
        else:
            self.Builder = builder.__all__[type]

        # Setup Events registry
        self.Events = EventHandler()
        for loop in ['k1', 'k2', 'a', 'b']:
            for event in ['on', 'in', 'out']:
                self.Events.__registry__['.'.join([loop, event])] = []

    def Build(self):
        '''
        Register `Builder.__listeners__`

        Iterates `n ** 2` "phases" plotting the topology of the
        "Fermat surface" of degree `n`.
        There are `n ** 2` `Patch`es per surface.

        `Builder` functions registered with 'on', 'in', 'out' events will be
        called in order once per nested loop.

        Add Rhino objects to document
        '''
        builder = self.Builder(self)

        if hasattr(self.Builder, '__listeners__') and callable(self.Builder.__listeners__):
            self.Events.register(builder.__listeners__())

        for k1 in self.RngK:
            self.Events.publish('k1.on', self, k1)
            self.Events.publish('k1.in', self, k1)

            for k2 in self.RngK:
                self.Events.publish('k2.on', self, k1, k2)
                self.Events.publish('k2.in', self, k1, k2)

                for a in self.RngU:
                    self.Events.publish('a.on', self, k1, k2, a)
                    self.Events.publish('a.in', self, k1, k2, a)

                    for b in self.RngV:
                        self.Events.publish('b.on', self, k1, k2, a, b)
                        self.Events.publish('b.in', self, k1, k2, a, b)
                        self.Events.publish('b.out', self, k1, k2, a, b)

                    self.Events.publish('a.out', self, k1, k2, a)

                self.Events.publish('k2.out', self, k1, k2)

            self.Events.publish('k1.out', self, k1)

        builder.Render(self)
