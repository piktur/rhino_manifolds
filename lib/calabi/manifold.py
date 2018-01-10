import System.Guid
import System.Drawing
import System.Enum
from math import cos, sin, pi
from scriptcontext import doc
# from rhinoscriptsyntax import AddObjectsToGroup, AddGroup, AddInterpCurve, frange
import rhinoscriptsyntax as rs
from Rhino.Geometry import Point3d
from Rhino.Geometry import NurbsCurve, Curve, Brep, Vector3d, CurveKnotStyle, Polyline

from events import EventHandler
from export import *
from calc import Calculate
import builder


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
        self.Edges = []
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

    def GetVCurve(self, i=-1):
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
        if self.__built__:
            return self

        self.__built__ = True
        return self

    def Fin(self):
        group = rs.AddGroup('Segment')
        objects = []

        for points in self.Curves:
            try:
                curve = rs.AddInterpCurve(points)
                objects.append(curve)
            except Exception:
                return None

        for points in self.VCurves:
            try:
                curve = rs.AddInterpCurve(points)
                objects.append(curve)
            except Exception:
                return None

        rs.AddObjectsToGroup(objects, group)
        doc.Groups.Add(objects)

        doc.Views.Redraw()


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
        self.MaxA = 1
        self.MaxB = pi / 2
        self.StepB = self.MaxB * self.Step
        self.RngK = range(self.n)
        self.RngA = rs.frange(-1, self.MaxA, self.Step)
        self.RngB = rs.frange(0, self.MaxB, self.StepB)

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
        '''
        Build Rhino objects and add to document
        '''
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
        self.Segments.append(segment)
        self.SegCnt += 1
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

    def LabeledPoints(self):
        # sorted = rs.SortPoints(self.Points)
        # `rs.SortPointList` will attempt to order points so that a Polyline may be formed
        sorted = rs.SortPointList(self.Points)

        for i, point in enumerate(sorted):
            dot = rs.AddTextDot(str(i), point)

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

    def CreatePolyline(self, points):
        points = rs.coerce3dpointlist(points, True)
        pl = Polyline(points)
        pl.DeleteShortSegments(doc.ModelAbsoluteTolerance)
        return pl

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

            # End loop after first iteration
            # if k1 == self.RngK[1]: break

            # outerSeg = self.AddSegment(k1, None, None)

            for k2 in self.RngK:
                self.Events.publish('k2.on', self, k1, k2)
                self.Events.publish('k2.in', self, k1, k2)

                # End loop after first iteration
                # if k2 == self.RngK[1]: break

                Seg = self.AddSegment(k1, k2, None)

                for a in self.RngA:
                    self.Events.publish('a.on', self, k1, k2, a)
                    self.Events.publish('a.in', self, k1, k2, a)

                    for b in self.RngB:
                        self.Events.publish('b.on', self, k1, k2, a, b)

                        point = self.Point(k1, k2, a, b)
                        self.Points.append(point)
                        self.PntCnt += 1

                        Seg.Points.append(point)
                        Seg.BPos += 1

                        if a == self.RngA[0]:
                            Seg.AddVCurve()

                        if b == self.RngB[0]:
                            Seg.AddCurve()
                            Seg.BPos = 0

                        try:
                            Seg.GetCurve(-1).append(point)
                        except AttributeError:
                            pass

                        try:
                            if b == self.RngB[-1]:
                                # TODO
                                pass
                            else:
                                # (self.SegCnt * Seg.BPos)
                                Seg.GetVCurve(-Seg.BPos).append(point)
                        except AttributeError:
                            pass

                        # Collect all edge points
                        if a == self.RngA[0] or a == self.RngA[-1]:
                            Seg.Edges.append(point)
                        if b == self.RngB[0] or b == self.RngB[-1]:
                            Seg.Edges.append(point)

                        # Collect points for each edge
                        if a == self.RngA[0]:
                            Seg.C4.append(point)
                        elif a == self.RngA[-1]:
                            Seg.C3.append(point)

                        if a == self.RngA[0] or a == self.RngA[-1]:
                            if b == self.RngB[0]:
                                Seg.C1.append(point)
                            if b == self.RngB[-1]:
                                Seg.C2.append(point)
                        elif b == self.RngB[0]:
                            Seg.C1.append(point)
                        elif b == self.RngB[-1]:
                            Seg.C2.append(point)

                        self.Events.publish('b.in', self, k1, k2, a, b, point)
                        self.Events.publish('b.out', self, k1, k2, a, b)

                    self.Events.publish('a.out', self, k1, k2, a)

                self.Events.publish('k2.out', self, k1, k2)

            self.Events.publish('k1.out', self, k1)

        for i, seg in enumerate(self.Segments):
            # Add labeled points to document
            # points = rs.SortPoints(seg.Edges)
            if rs.GetBoolean('Add Labeled Points',  ('Proceed?', 'No', 'Yes'), (True)) is not None:
                for i, point in enumerate(seg.Edges):
                    point = rs.AddPoint(point)
                    dot = rs.AddTextDot(str(i), point)


            # Segment Edges
            group = rs.AddGroup('Edges' + str(i))
            lines = []
            line_ids = []

            for points in seg.C3, seg.C4:
                curve = self.CreateInterpolatedCurve(points)
                id = doc.Objects.AddCurve(curve)
                line_ids.append(id)
                lines.append(curve)

            for points in seg.C1, seg.C2:
                curve = self.CreatePolyline(points)
                id = doc.Objects.AddPolyline(curve)
                line_ids.append(id)
                lines.append(curve)

            rs.AddObjectsToGroup(line_ids, group)
            doc.Groups.Add(line_ids)


            # Add Boundary Representation from lines
            # TODO incompatible with Polyine
            # brep = Brep.CreateEdgeSurface(lines)
            # doc.Objects.AddBrep(brep)


            # Inner curves
            if rs.GetBoolean('Add Inner Curves',  ('Proceed?', 'No', 'Yes'), (True)) is not None:
                group = rs.AddGroup('Curves' + str(i))
                curves = []
                curve_ids = []

                for i, points in enumerate(seg.Curves):
                    if i % 2 == 1:
                        try:
                            curve = self.CreateInterpolatedCurve(points)
                            id = doc.Objects.AddCurve(curve)
                            curve_ids.append(id)
                            curves.append(curve)
                        except:
                            None

                for i, points in enumerate(seg.VCurves):
                    if i % 2 == 1:
                        try:
                            curve = self.CreateInterpolatedCurve(points)
                            id = doc.Objects.AddCurve(curve)
                            curve_ids.append(id)
                            curves.append(curve)
                        except:
                            None

                rs.AddObjectsToGroup(curve_ids, group)
                doc.Groups.Add(curve_ids)

            doc.Views.Redraw()
