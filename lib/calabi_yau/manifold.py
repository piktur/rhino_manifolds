import System.Guid
import System.Drawing
import System.Enum
from math import cos, sin, pi, fabs
from scriptcontext import doc
# from rhinoscriptsyntax import AddObjectsToGroup, AddGroup, frange
import rhinoscriptsyntax as rs

from events import EventHandler
import builder


class Manifold:
    '''
    Adaptation of [Andrew J. Hanson](https://www.cs.indiana.edu/~hansona/papers/CP2-94.pdf) algorithm.

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
        # TODO Verify angle calculation
        #   t = pi / 4
        #   self.Alpha = deg - t
        #   self.Alpha = deg * t
        #   self.Alpha = deg * pi
        #   deg = (t = range(0, 1, 0.1))[1]
        #   (deg + 0.25) * pi
        # TODO We should also set a range through 0 > 2 Pi as in [plot_1.nb](/examples/mathematica/plot_1.nb)
        self.Alpha = deg * pi
        self.Step = step
        self.Scale = scale
        self.Offset = offset

        # NOTE `U` -- "xi" must be odd to guarantee passage through fixed points at
        # (theta, xi) = (0, 0) and (theta, xi) = (pi / 2, 0)
        # [Table 1](https://www.cs.indiana.edu/~hansona/papers/CP2-94.pdf)
        self.U = int(11)
        self.V = int(11)

        self.MinU = -1
        self.MaxU = 1
        self.StepU = fabs(self.MaxU - self.MinU) / float(self.U - 1)

        self.MinV = 0
        self.MaxV = float(pi / 2)
        self.StepV = fabs(self.MaxV - self.MinV) / float(self.V - 1)
        # self.StepV = self.MaxV * self.Step

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

    def Phase(self):
        '''
        Iterates `n ** 2` "phases" plotting the topology of the
        "Fermat surface" of degree `n`.
        There are `n ** 2` `Patch`es per surface.

        `Builder` functions registered with 'on', 'in', 'out' events will be
        called in order once per nested loop.
        '''
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

    def Build(self):
        '''
        Register `Builder.__listeners__`
        Step through Phase loop
        Add Rhino objects to document
        '''
        builder = self.Builder(self)

        if hasattr(self.Builder, '__listeners__') and callable(self.Builder.__listeners__):
            self.Events.register(builder.__listeners__())

        self.Phase()
        builder.Render(self)
