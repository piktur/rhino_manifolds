from math import cos, sin, pi
from rhinoscriptsyntax import frange
from Rhino.Geometry import Point3d

from events import EventHandler
from export import *
from calc import Calculate
import builder

__cached__ = False


def GenerateMatrix(inc=15):
    '''
    TODO Generate multiple manifolds and arrange in grid
    '''


class Segment:
    '''
    Attributes:
        Meshes : list<Rhino.Geometry.Mesh>
    '''
    __slots__ = ['Points', 'Curves', 'Meshes', 'Surfaces']

    # def __init__(self, cy):
    #     Builder.__init__(self, cy)
    #     self.C1 = None  # bound_start
    #     self.C2 = None  # bound_end
    #     self.C3 = None  # curve_outer
    #     self.C4 = None  # curve_inner
    #     self.SubCurves = None
    #     self.SubPoints = None
    #     self.Curves = []
    #     self.Breps = []
    #     self.U = []
    #     self.V = []
    #
    # def __listeners__(self):
    #     return {
    #         'k1.on': [self.Before],
    #         'a.in': [self.Build]
    #     }
    #
    # def Before(self, cy, *args):
    #     # k1, k2, a = args
    #
    #     self.C1 = []
    #     self.C2 = []
    #     self.C3 = []
    #     self.C4 = []
    #     self.SubCurves = []
    #     self.SubPoints = []
    #     # self.V.append([])
    #     self.U.append([])
    #
    # def Build(self, cy, *args):
    #     '''
    #     TODO Ensure domain corner anchored to centre point
    #     TOOD Group points by surface domain
    #     TODO Group quad surface curves
    #     TODO Fit surface to domain points
    #     '''
    #     k1, k2, a, b, point = args
    #
    #     self.SubPoints.append(point)
    #
    #     u = self.U[-1]
    #     # self.V[-1]
    #
    #     if a == cy.RngA[0]:
    #         self.C4.append(point)
    #         # u.append(point)
    #         # v.append(point)
    #     elif a == cy.RngA[-1]:
    #         self.C3.append(point)
    #         # u.append(point)
    #         # v.append(point)
    #     elif b == cy.RngB[0]:  # is this necessary?
    #         self.C1.append(point)
    #     elif b == cy.RngB[-1]:
    #         self.C2.append(point)
    #
    #     # TODO do we need to be adding this to the front of the array arr.insert(0, val)
    #     if a == cy.RngA[0] or a == cy.RngA[-1]:
    #         u.append(point)
    #         # v.append(point)
    #         if b == cy.RngB[0]:
    #             self.C1.append(point)
    #         elif b == cy.RngB[-1]:
    #             self.C2.append(point)


class Manifold:
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
        SegCnt : int
        PntCnt : int
            Is the cumulative position within `ParametricPlot3d` loop --
            equiv to `len(self.Points)`
        Segments : list<Segment>
        Points : list<Rhino.Geometry.Point3d>
        Builder : class
    '''

    __slots__ = ['n', 'Alpha', 'Step', 'Scale', 'MaxA', 'MaxB', 'StepB',
                 'RngK', 'RngA', 'RngB', 'SegCnt', 'PntCnt' 'Segs', 'Points']

    def __init__(self, n=1, deg=1.0, step=0.1, scale=1, type=4):
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
        self.MaxA = float(1)
        self.MaxB = float(pi / 2)
        self.StepB = self.MaxB * self.Step
        self.RngK = range(self.n)
        self.RngA = frange(float(-1), self.MaxA, self.Step)
        self.RngB = frange(float(0), self.MaxB, self.StepB)

        self.SegCnt = 0
        self.PntCnt = 0
        self.Segments = []
        self.Points = []
        self.Builder = builder.__all__[type]

        # Setup Events registry
        self.Events = EventHandler()
        for d in ['k1', 'k2', 'a', 'b']:
            for event in ['on', 'in', 'out']:
                self.Events.__registry__['.'.join(d + event)] = []

    def Build(self):
        builder = self.Builder(self)
        # Register listeners if defined
        if hasattr(self.Builder, '__listeners__') and callable(self.Builder.__listeners__):
            self.Events.register(builder.__listeners__())
        self.ParametricPlot3D()
        builder.Render(self)

    def AddSegment(self, k1, k2, a):
        if a == self.RngA[0] and k2 == self.RngK[0] and k1 == self.RngK[0]:
            segment = Segment()
            self.Segments.append(segment)
            self.SegCnt += 1
            print self.SegCnt
            return segment

    def Point(self, *args):
        '''
        Calculate point coords and return Rhino.Geometry.Point3d
        TODO Confirm; are we always moving right to left?
        '''
        coords = map(
            lambda i: i * self.Scale,
            Calculate(self.n, self.Alpha, *args))
        return Point3d(*coords)

    def ParametricPlot3D(self):
        '''
        Registered 'on', 'in', 'out' callbacks will be executed in turn per nested loop.

        Examples:
        ```
            # Calculate iterations
            self.n * self.n * len(self.RngA) * len(self.RngB)
        ````
        '''
        for k1 in self.RngK:
            self.Events.publish('k1.on', self, k1)
            self.Events.publish('k1.in', self, k1)

            # Break out first iteration
            # if k1 == self.RngK[1]: break

            for k2 in self.RngK:
                self.Events.publish('k2.on', self, k1, k2)
                self.Events.publish('k2.in', self, k1, k2)

                # Break out first iteration
                # if k2 == self.RngK[1]: break

                segment = self.AddSegment(k1, k2, a)

                for a in self.RngA:
                    self.Events.publish('a.on', self, k1, k2, a)
                    self.Events.publish('a.in', self, k1, k2, a)

                    for b in self.RngB:
                        self.Events.publish('b.on', self, k1, k2, a, b)

                        point = self.Point(k1, k2, a, b)
                        self.Points.append(point)
                        self.PntCnt += 1

                        self.Events.publish('b.in', self, k1, k2, a, b, point)
                        self.Events.publish('b.out', self, k1, k2, a, b)

                    self.Events.publish('a.out', self, k1, k2, a)

                self.Events.publish('k2.out', self, k1, k2)

            self.Events.publish('k1.out', self, k1)
