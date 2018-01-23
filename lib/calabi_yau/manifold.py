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
    Adaptation of [Andrew J. Hanson](https://www.cs.indiana.edu/~hansona/papers/CP2-94.pdf) "superquadric" algorithm.

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
    __slots__ = ['n', 'Alpha', 'Step', 'Scale',

                 'Phases',
                 'MinU', 'MaxU', 'StepU', 'CentreU',
                 'MinV', 'MaxV', 'StepV', 'CentreU',
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
        t = pi / 4
        self.Alpha = deg * t
        self.Step = step
        self.Scale = scale
        self.Offset = offset

        self.U = int(11)
        self.V = int(11)

        self.MinU = -1
        self.MaxU = 1
        # NOTE `U` -- "xi" must be odd to guarantee passage through fixed points at
        # (theta, xi) = (0, 0) and (theta, xi) = (pi / 2, 0)
        # [Table 1](https://www.cs.indiana.edu/~hansona/papers/CP2-94.pdf)
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

        self.Phases = []

        # NOTE [Figure 5](https://www.cs.indiana.edu/~hansona/papers/CP2-94.pdf)
        # Demonstrates phase occurrence. Build algorithm to group accordingly.
        for i, k1 in enumerate(self.RngK):
            for i, k2 in enumerate(self.RngK):
                self.Phases.append([k1, k2])

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

    def Plot3D(self):
        '''
        Iterates `n * n` "phases" plotting the topology of the "Fermat surface" of degree `n`. There are `n * n` `Patch`es per surface.

        Registered 'on', 'in', 'out' callbacks will be executed in turn per nested loop.
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

        return self

    def Build(self):
        '''
        Build Rhino objects and add to document
        '''
        builder = self.Builder(self)

        if hasattr(self.Builder, '__listeners__') and callable(self.Builder.__listeners__):
            self.Events.register(builder.__listeners__())

        self.Plot3D()
        builder.Render(self)
