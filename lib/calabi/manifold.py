from math import cos, sin, pi
from scriptcontext import doc
# from rhinoscriptsyntax import AddObjectsToGroup, AddGroup, AddInterpCurve, frange
import rhinoscriptsyntax as rs
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
    __slots__ = [
        'Points', 'Curves', 'Meshes', 'Surfaces',
        'C1', 'C2', 'C3', 'C4', 'U', 'V', '__built__'
    ]

    def __init__(self, cy):
        self.CalabiYau = cy
        self.Points = []
        self.Curves = []
        self.VCurves = []
        self.Meshes = []
        self.Surfaces = []
        self.C1 = []  # bound_start
        self.C2 = []  # bound_end
        self.C3 = []  # curve_outer
        self.C4 = []  # curve_inner
        self.U = []
        self.V = []
        self.BPos = -1
        self.__built__ = False

    def AddCurve(self):
        points = []
        self.Curves.append(points)
        return points

    def GetCurve(self, i=-1):
        try:
            return self.Curves[i]
        except IndexError:
            return

    def AddVCurve(self):
        points = []
        self.VCurves.append(points)
        return points

    def GetVCurve(self, i): # -1
        try:
            return self.VCurves[i]
        except IndexError:
            return

    def Build(self, cy, *args):
        '''
        TODO Ensure domain corner anchored to centre point
        TOOD Group points by surface domain
        TODO Group quad surface curves
        TODO Fit surface to domain points
        '''
        # if self.__built__:
        #     return self

        # k1, k2, a, b, point = args
        #
        # if b == cy.RngB[0]:
        #     self.AddCurve()
        #     self.BPos = -1
        # else:
        #     self.BPos -= 1
        #
        # # if a == cy.RngA[0] or a == cy.RngA[-1]: self.AddVCurve()
        # # if k2 == cy.RngK[0]: self.AddVCurve()
        # # if a == cy.RngA[0]: self.AddVCurve()
        #
        # # We will need to find the correct VCurve there will be one per b
        #
        # # if a == cy.RngA[0] or a == cy.RngA[-1]:
        # #     try:
        # #         self.GetVCurve().append(point)
        # #     except AttributeError:
        # #         pass
        #
        # # if b == cy.RngB[0]:
        # try:
        #     self.GetCurve(-1).append(point)
        #     self.GetVCurve(self.BPos).append(point)
        # except AttributeError:
        #     pass
        #
        # if a == cy.RngA[0]:
        #     self.C4.append(point)
        #     # u.append(point)
        #     # v.append(point)
        # elif a == cy.RngA[-1]:
        #     self.C3.append(point)
        #     # u.append(point)
        #     # v.append(point)
        # elif b == cy.RngB[0]:  # is this necessary?
        #     self.C1.append(point)
        # elif b == cy.RngB[-1]:
        #     self.C2.append(point)
        #
        # # TODO do we need to be adding this to the front of the array arr.insert(0, val)
        # if a == cy.RngA[0] or a == cy.RngA[-1]:
        #
        #     # u.append(point)
        #     # v.append(point)
        #     if b == cy.RngB[0]:
        #         self.C1.append(point)
        #     elif b == cy.RngB[-1]:
        #         self.C2.append(point)

        # self.__built__ = True
        return self

    def Fin(self):
        # ids = []

        for points in self.Curves:
            try:
                curve = rs.AddInterpCurve(points)
            except:
                return None
            # ids.append(curve)

        for points in self.VCurves:
            try:
                curve = rs.AddInterpCurve(points)
                # print curve.Id
                # ids.append(curve)
            except:
                return None

        # strGroup = rs.AddGroup("NewGroup")
        # rs.AddObjectsToGroup(ids, strGroup)
        # index = doc.Groups.Add(ids)

        # doc.Views.Redraw()


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
        self.RngA = rs.frange(float(-1), self.MaxA, self.Step)
        self.RngB = rs.frange(float(0), self.MaxB, self.StepB)

        self.SegCnt = 0
        self.PntCnt = 0
        self.InnerSegCnt = 0
        self.OuterSegCnt = 0
        self.InnerSegments = []
        self.OuterSegments = []
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

    def GetSegment(self, i=-1):
        return self.InnerSegments[i]

    def AddSegment(self, k1, k2, a):
        # if a == self.RngA[0] and k2 == self.RngK[0] and k1 == self.RngK[0]
        segment = Segment(self)
        self.OuterSegments.append(segment)
        self.OuterSegCnt += 1
        return segment
        # else:
        #     return self.GetSegment()

    def AddInnerSegment(self, k1, k2, a):
        # if a == self.RngA[0] and k2 == self.RngK[0] and k1 == self.RngK[0]
        segment = Segment(self)
        self.InnerSegments.append(segment)
        self.InnerSegCnt += 1
        return segment
        # else:
        #     return self.GetSegment()

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

                # TODO Add group quad bound group containing inner curves
                #
                #
                outerSeg = self.AddSegment(k1, k2, None)
                APos = 1

                for a in self.RngA:
                    self.Events.publish('a.on', self, k1, k2, a)
                    self.Events.publish('a.in', self, k1, k2, a)

                    # innerSeg = self.AddInnerSegment(k1, k2, a)


                    APos += 1
                    outerSeg.AddCurve()
                    outerSeg.BPos = 0

                    for b in self.RngB:
                        self.Events.publish('b.on', self, k1, k2, a, b)

                        point = self.Point(k1, k2, a, b)
                        # if round(point.X) == round(24.139) and round(point.Y) == round(-18.384) and round(point.Z) == round(116.073):
                        #     print (k1, k2, a, b)

                        self.Points.append(point)
                        self.PntCnt += 1

                        outerSeg.Points.append(point)

                        #  and b <= self.RngB[3]
                        # if a == self.RngA[0]: # or a == self.RngA[1]:
                        #     doc.Objects.AddPoint(point)
                        #     print (k1, k2, a, b)
                        #     if rs.GetBoolean('Proceed',  ('Proceed?', 'No', 'Yes'), (True)) is None: return
                        # else:
                        #     return

                        if a == self.RngA[0]:
                            outerSeg.AddVCurve() # VCurves.append([])

                        # if b == self.RngB[0]:
                        #     outerSeg.AddCurve()
                        #     outerSeg.BPos = 0
                        # else:
                        outerSeg.BPos += 1

                        # if a == self.RngA[0] or a == self.RngA[-1]: self.AddVCurve()
                        # if k2 == self.RngK[0]: self.AddVCurve()
                        # if a == self.RngA[0]: self.AddVCurve()

                        # if a == self.RngA[0] or a == self.RngA[-1]:
                        #     try:
                        #         self.GetVCurve().append(point)
                        #     except AttributeError:
                        #         pass

                        try:
                            # if a == self.RngA[0] and b == self.RngB[0]:
                            #     outerSeg.GetCurve(0).append(point)
                            # else:
                            outerSeg.GetCurve(-1).append(point)

                            # self.SegCnt * segment.BPos
                            # segment.GetVCurve(-segment.BPos).append(point)
                        except AttributeError:
                            # print (k1, k1, APos, BPos)
                            pass

                        try:
                            if b == self.RngB[-1]:
                                # outerSeg.GetVCurve(-outerSeg.BPos).append(point)
                                None
                            else:
                                outerSeg.GetVCurve(-outerSeg.BPos).append(point)
                        except AttributeError:
                            print (k1, k1, APos, outerSeg.BPos)
                            pass

                        if a == self.RngA[0]:
                            outerSeg.C4.append(point)
                        elif a == self.RngA[-1]:
                            outerSeg.C3.append(point)
                        elif b == self.RngB[0]:  # is this necessary?
                            outerSeg.C1.append(point)
                        elif b == self.RngB[-1]:
                            outerSeg.C2.append(point)

                        # TODO do we need to be adding this to the front of the array arr.insert(0, val)
                        if a == self.RngA[0] or a == self.RngA[-1]:
                            if b == self.RngB[0]:
                                outerSeg.C1.append(point)
                            elif b == self.RngB[-1]:
                                outerSeg.C2.append(point)

                        # innerSeg.Build(self, k1, k2, a, b, point)

                        # if b == self.RngB[-1]:
                        #     outerSeg.AddCurve()
                        #     outerSeg.BPos = 0

                        self.Events.publish('b.in', self, k1, k2, a, b, point)
                        self.Events.publish('b.out', self, k1, k2, a, b)

                    self.Events.publish('a.out', self, k1, k2, a)

                self.Events.publish('k2.out', self, k1, k2)

            self.Events.publish('k1.out', self, k1)

        # for seg in self.InnerSegments:
        #     print len(seg.VCurves)
        #     # seg.Fin()

        for seg in self.OuterSegments:
            group = rs.AddGroup('NewGroup')
            objects = []

            for points in seg.VCurves:
                try:
                    # print len(points)
                    curve = rs.AddInterpCurve(points)
                    objects.append(curve)
                except: None

                # doc.Views.Redraw()

            for points in seg.Curves:
                try:
                    curve = rs.AddInterpCurve(points)
                    objects.append(curve)
                except: None

                doc.Views.Redraw()

            # for points in seg.C1, seg.C2, seg.C3, seg.C4:
            #     curve = rs.AddInterpCurve(points)
            #     objects.append(curve)

            rs.AddObjectsToGroup(objects, group)

            index = doc.Groups.Add(objects)


            # return
