import System.Guid
import System.Drawing
import System.Enum
from math import cos, sin, pi, fabs
from scriptcontext import doc
# from rhinoscriptsyntax import AddObjectsToGroup, AddGroup, frange
import rhinoscriptsyntax as rs
from Rhino.Geometry import Point3d
from Rhino.Collections import Point3dList, CurveList

from events import EventHandler
from export import *
from calc import Calculate
import builder


class Patch:
    '''
    Attributes:
        Points : Rhino.Collections.Point3dList
        Surface : Rhino.Geometry.NurbsSurface
        Surface : list<Rhino.Geometry.NurbsSurface>
        Brep : Rhino.Geometry.Brep
        Mesh : Rhino.Geometry.Mesh
        Edges : list<Rhino.Geometry.NurbsCurve>
    '''
    __slots__ = [
        'CalabiYau', 'Points', 'Surface', 'Surfaces', 'Brep', 'Mesh', 'Edges',
        'C1', 'C2', 'C3', 'C4',
        '__built__'
    ]

    def __init__(self, cy):
        self.CalabiYau = cy
        self.Points = Point3dList()
        self.Surface = None
        self.Surfaces = []
        self.Brep = None
        self.Mesh = None
        self.Edges = CurveList()
        self.C1 = []
        self.C2 = []
        self.C3 = []
        self.C4 = []
        self.__built__ = False


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
        Offset : int
        Phases : list
        MaxU : float
        MaxV : float
        StepV : float
        RngK : range
        RngU : range
        RngV : range
        Points : list<Rhino.Geometry.Point3d>
        PointCount : int
            Cumulative position within `Plot3D` nested loop -- equiv to `len(self.Points)`
        Patches : list<Patch>
        PatchCount : int
        Builder : class
    '''

    __slots__ = ['n', 'Alpha', 'Step', 'Scale',
                 'Phases', 'MaxU', 'MaxV', 'StepV',
                 'RngK', 'RngU', 'RngV',
                 'Points', 'Point', 'PointCount',
                 'Patches', 'Patch', 'PatchCount']

    def __init__(self, n=1, deg=1.0, step=0.1, scale=1, offset=0, type=4):
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
        self.Alpha = deg * pi
        self.Step = step
        self.Scale = scale
        self.Offset = float(offset)

        self.U = int(11)
        self.V = int(11)
        self.MinU = -1
        self.MaxU = 1
        # NOTE `StepU` -- "xi" must be odd to guarantee passage through fixed points at (theta, xi) = (0, 0) and (theta, xi) = (pi / 2, 0) [Table 1](https://www.cs.indiana.edu/~hansona/papers/CP2-94.pdf)
        self.StepU = fabs(self.MaxU - self.MinU) / float(self.U - 1)
        self.MinV = 0
        self.MaxV = float(pi / 2)
        self.StepV = fabs(self.MaxV - self.MinV) / float(self.V - 1)
        # self.StepV = self.MaxV * self.Step
        self.RngK = rs.frange(0, n - 1, 1) # range(self.n)
        self.RngU = rs.frange(self.MinU, self.MaxU, self.StepU)
        self.RngV = rs.frange(self.MinV, self.MaxV, self.StepV)

        self.Phases = []

        # NOTE [Figure 5](https://www.cs.indiana.edu/~hansona/papers/CP2-94.pdf) Demonstrates phase occurrence. Build algorithm to group accordingly.
        for i, k1 in enumerate(self.RngK):
            for i, k2 in enumerate(self.RngK):
                self.Phases.append([k1, k2])

        self.Points = []
        self.Point = None
        self.PointCount = 0
        self.Patches = []
        self.Patch = None
        self.PatchCount = 0

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

    def Surfaces(self):
        return map(lambda e: e.Surfaces, self.Patches)

    def Breps(self):
        return map(lambda e: e.Brep, self.Patches)

    def Edges(self):
        return map(lambda e: e.Edges, self.Patches)

    def Meshes(self):
        return map(lambda e: e.Mesh, self.Patches)

    def Build(self):
        '''
        Build Rhino objects and add to document
        '''
        self.Events.register({
            'k2.on': [self.AddPatch],
            'b.on': [self.AddPoint],
            'b.in': [],
            'k2.out': []
        })

        builder = self.Builder(self)

        # Register builder's listeners
        if hasattr(self.Builder, '__listeners__') and callable(self.Builder.__listeners__):
            self.Events.register(builder.__listeners__())

        self.Plot3D()
        builder.Render(self)

    def AddPatch(self, *args):
        '''
        Add `self.n ** 2`th Patch
        '''
        self.Patch = Patch(self)
        self.Patches.append(self.Patch)
        self.PatchCount += 1
        return self.Patch

    def AddPoint(self, *args):
        '''
        Calculate point coordinates and return Rhino.Geometry.Point3d
        '''
        coords = map(
            lambda i: (i * self.Scale) + self.Offset,
            Calculate(self.n, self.Alpha, *args[1:])
        )
        self.Point = Point3d(*coords)
        self.Points.Add(self.Point)
        self.Patch.Points.Add(self.Point)
        self.PointCount += 1
        return self.Point

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
                    # if a == self.RngU[0] and k2 == self.RngK[0] and k1 == self.RngK[0]

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
