import System.Guid
import System.Enum
from System.Drawing import Color
import cmath
from math import pi
from scriptcontext import doc
import rhinoscriptsyntax as rs
from Rhino.Geometry import Brep, ControlPoint, Curve, CurveKnotStyle, Mesh, NurbsCurve, NurbsSurface, Point3d, Vector3d
from Rhino.Collections import Point3dList, CurveList

import calabi_yau.calc as Alg

reload(Alg)


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
        'Analysis',
        'Points',
        'Surface', 'Surfaces',
        'Brep',
        'MeshA', 'MeshB',
        'Edges',
        '__built__'
    ]

    def __init__(self, cy):
        self.CalabiYau = cy
        self.Analysis = {}
        self.Points = Point3dList()
        self.Surfaces = []
        # self.Edges = []
        # self.Brep = None
        self.__built__ = False


class Builder:
    '''
    Subdivisions ensure geometry comes together at `Patch.Analysis['centre']`

    Attributes:
        CalabiYau : CalabiYau.Manifold
        Points : list<Rhino.Geometry.Point3d>
        Point : Rhino.Geometry.Point3d
        PointCount : int
            Cumulative position within `Plot3D` nested loop --
            equiv to `len(self.Points)`
        Patches : list<Patch>
        Patch : Patch
        PatchCount : int
    '''
    __slots__ = ['CalabiYau',
                 'Analysis',
                 'Points', 'Point', 'PointCount',
                 'Patches', 'Patch', 'PatchCount',
                 '__colour__']

    def __init__(self, cy):
        self.CalabiYau = cy

        self.Points = []
        self.Point = None
        self.PointCount = 0

        self.Patches = []
        self.Patch = None
        self.PatchCount = 0
        self.__colour__ = Builder.Colours()

        self.Analysis = Alg.PointAnalysis
        self.Analysis['g'] = Alg.Genus(cy.n)
        self.Analysis['chi'] = Alg.EulerCharacteristic(cy.n)

    def Build(self, *args, **kwargs):
        pass

    def Surfaces(self):
        return map(lambda e: e.Surfaces, self.Patches)

    def Breps(self):
        return map(lambda e: e.Brep, self.Patches)

    def Edges(self):
        return map(lambda e: e.Edges, self.Patches)

    def Meshes(self):
        return [self.MeshA, self.MeshB]

    def Render(self, cb, cy, group, *args, **kwargs):
        '''
        Evaluates `cb()` and assigns Geometry to patch layer.
        '''
        ids = []

        for k1, phase in enumerate(Builder.chunk(self.Patches, cy.n)):
            parent = rs.AddLayer('::'.join([group, str(k1)]))

            for k2, patch in enumerate(phase):
                layer = rs.AddLayer('::'.join([parent, str(k2)]), self.Colour(cy.n, k1, k2))
                cb(phase, patch, layer, ids)

        doc.Views.Redraw()

        return ids

    def AddPatch(self, cy, *args):
        '''
        Add `self.n ** 2`th Patch
        '''
        self.Patch = Patch(cy)
        self.Patches.append(self.Patch)
        self.PatchCount += 1

        return self.Patch

    def PointAnalysis(self, cy, *args):
        '''
        [Figure 4](https://www.cs.indiana.edu/~hansona/papers/CP2-94.pdf)
        Store 3d point coordinates at significant angles/U count
        '''
        k1, k2, xi, theta = args
        _ = self.Analysis

        # if self.PointCount < cy.U * cy.V:
        #     if round(xi, 1) == (cy.MinU + cy.MaxU):
        #         print round(xi, 1)
        #         if round(theta, 5) == round(pi / 2, 5):
        #             print theta

        _['minU'] = round(xi, 1) == cy.MinU  # -1
        _['midU'] = round(xi, 1) == (cy.MinU + cy.MaxU)  # 0
        _['maxU'] = round(xi, 1) == cy.MaxU  # 1

        # TODO what about pi / n
        # TODO what about pi / an odd number
        _['theta == 0'] = round(theta, 5) == float(0)
        _['theta == 45'] = round(theta, 5) == round(pi / 4, 5)
        _['theta == 90'] = round(theta, 5) == round(pi / 2, 5)

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

        return _

    def BuildPoint(self, cy, *args):
        '''
        Calculate point coordinates and return Rhino.Geometry.Point3d
        '''
        k1, k2, a, b = args

        coords = map(
            lambda i: (i * cy.Scale),
            Alg.CalculatePoint(cy.n, cy.Alpha, *args)  # args[1:]
        )
        x, y, z = coords

        OffsetX, OffsetY = cy.Offset
        coords[0] = x + OffsetX
        coords[1] = y + OffsetY

        self.Point = Point3d(*coords)
        self.Points.Add(self.Point)
        self.Patch.Points.Add(self.Point)
        self.PointCount += 1

        self.PointAnalysis(cy, *args)

        return self.Point

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
    def Colours():
        '''
        Returns 2D list of colours 10 * 4
        '''
        arr = []
        for i in range(25, 255, 25):  # 255 / 25 == 10
            arr.append((
                Color.FromArgb(i, 0, i),  # Red-Blue
                Color.FromArgb(0, 0, i),  # Blue
                Color.FromArgb(0, i, i),  # Green-Blue
                Color.FromArgb(0, i, 0)   # Green
            ))

        return arr

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
    def chunk(list, size):
        '''
        Yield successive chunks of `size` from `list`.
        '''
        for i in range(0, len(list), size):
            yield list[i:i + size]

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

    def __rendered__(self, obj):
        '''
        Confirm `obj` present in document Guid
        '''
        if obj == System.Guid.Empty:
            raise Exception('RenderError')

        return True


class PointCloudBuilder(Builder):
    __slots__ = Builder.__slots__

    def __init__(self, *args):
        Builder.__init__(self, *args)

    def Render(self, cy, *args):
        parent = rs.AddLayer('Points')

        def cb(phase, patch, layer, ids):
            for point in patch.Points:
                id = doc.Objects.AddPoint(point)
                ids.append(id)
                rs.ObjectLayer(id, layer)

        Builder.Render(self, cb, cy, parent, *args)


class MeshBuilder(Builder):
    __slots__ = Builder.__slots__ + ['MeshA', 'MeshB', 'MeshCount']

    def __init__(self, cy):
        Builder.__init__(self, cy)
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

    def AddMesh(self, cy, *args):
        # k1, k2 = args

        self.Patch.MeshA = Mesh()
        self.Patch.MeshB = Mesh()

    def IncrementMeshCount(self, cy, *args):
        k1, k2, a, b = args

        if a == cy.RngU[0] and k2 == cy.RngK[0] and k1 == cy.RngK[0]:
            self.MeshCount += 1

    def BuildFaces(self, mesh, cy, k1, k2, a, b):
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

    def BuildMesh(self, cy, *args):
        k1, k2, a, b = args

        if a > cy.RngU[0] and b > cy.RngV[0]:
            if a <= cy.RngU[cy.CentreU]:
                self.MeshA = Mesh()
                self.BuildFaces(self.MeshA, cy, *args)
                self.Patch.MeshA.Append(self.MeshA)
            else:
                self.MeshB = Mesh()
                self.BuildFaces(self.MeshB, cy, *args)
                self.Patch.MeshB.Append(self.MeshB)

    def WeldMesh(self, cy, *args):
        self.Patch.MeshA.Weld(pi)
        self.Patch.MeshB.Weld(pi)

    def Render(self, cy, *args):
        parent = rs.AddLayer('Meshes')

        def cb(phase, patch, layer, ids):
            for i, mesh in enumerate([patch.MeshA, patch.MeshB]):
                id = doc.Objects.AddMesh(mesh)
                ids.append(id)
                rs.ObjectLayer(id, layer)

        Builder.Render(self, cb, cy, parent, *args)


class CurveBuilder(Builder):
    __slots__ = Builder.__slots__ + [
        'Edges',
        'A', 'B', 'C', 'D',
        'A1', 'B1', 'C1', 'D1',
        'A2', 'B2', 'C2', 'D2'
    ]

    def __init__(self, cy):
        Builder.__init__(self, cy)
        self.VCount = 0

    def __listeners__(self):
        listeners = Builder.__listeners__(self)
        listeners['k2.in'].append(self.AddEdges)
        listeners['b.in'].append(self.PlotEdges)
        listeners['k2.out'].extend([self.BuildEdges])

        return listeners

    def AddEdges(self, cy, *args):
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

    def PlotEdges(self, cy, *args):
        '''
        [#10](https://bitbucket.org/kunst_dev/snippets/issues/10/curve-generation)
        '''
        k1, k2, a, b = args

        # "rails"
        if a == cy.RngU[0]:  # self.Analysis['min90']:
            self.A.append(self.Point)
            self.A1.append(self.Point)

        if a == cy.RngU[cy.CentreU]:  # self.Analysis['mid90']:
            self.C1.append(self.Point)
            self.C2.append(self.Point)

        if a == cy.RngU[-1]:  # self.Analysis['max90']:
            self.C.append(self.Point)
            self.A2.append(self.Point)

        # "cross-sections"
        if b == cy.RngV[0]:
            self.B.append(self.Point)

            if len(self.B1) <= cy.CentreV:
                self.B1.append(self.Point)
            if len(self.B1) > cy.CentreV:
                self.B2.append(self.Point)

        if b == cy.RngV[-1]:
            self.D.append(self.Point)
            if len(self.D1) <= cy.CentreV:
                self.D1.append(self.Point)
            if len(self.D1) > cy.CentreV:
                self.D2.append(self.Point)

    def BuildEdges(self, cy, *args):
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
        # for points in (self.A1, self.C1):
        #     Edges1.Add(Builder.BuildInterpolatedCurve(points))
        # for points in (self.A2, self.C2):
        #     Edges2.Add(Builder.BuildInterpolatedCurve(points))

        Edges1.Add(Builder.BuildInterpolatedCurve(self.A1))
        Edges2.Add(Builder.BuildInterpolatedCurve(self.A2))

        Edges1.Add(Builder.BuildInterpolatedCurve(self.C1))
        Edges2.Add(Builder.BuildInterpolatedCurve(self.C2))

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

    def Render(self, cy, *args):
        # rs.AddLayer('Centre', Color.Magenta)
        parent = rs.AddLayer('Curves')

        for k1, phase in enumerate(Builder.chunk(self.Patches, cy.n)):
            for k2, patch in enumerate(phase):
                Edges, Edges1, Edges2 = patch.Edges
                A, C, B, D = Edges
                A1, C1, B1, D1 = Edges1
                A2, C2, B2, D2 = Edges2

                for e in (1, 2):
                    for i, char in enumerate(('A', 'C', 'B', 'D')):
                        var = char + str(e)
                        colour = self.__colour__[-k1][i]
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


class SurfaceBuilder(Builder):
    '''
    Build quadrilateral surfaces.
    See [Example](https://bitbucket.org/snippets/kunst_dev/X894E8)
    '''

    __slots__ = Builder.__slots__ + [
        'UDegree', 'VDegree',
        '__points',
        'UCount', 'VCount'
    ]

    def __init__(self, cy):
        Builder.__init__(self, cy)
        # Note: Polysurface created if U and V degrees differ.
        self.UDegree = 3
        self.VDegree = 3
        self.UCount = 0
        self.VCount = 0

    def __listeners__(self):
        listeners = Builder.__listeners__(self)
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
        self.__points = Point3dList()
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

    def AddSurfaceSubdivision(self, cy, *args):
        k1, k2, a = args

        if self.Analysis['mid90']:  # a == cy.RngU[cy.CentreU]
            self.BuildSurface(cy, *args)  # Finalise current subdivision
            self.AddSurface(cy, *args)  # Begin next subdivision
            self.__points = Point3dList(self.Points[-cy.U:])
            self.IncrementUCount()

    def PlotSurface(self, cy, *args):
        k1, k2, a, b = args

        self.__points.Add(self.Point)

    def BuildSurface(self, cy, *args):
        '''
        TODO Add `Weight` to `self.Patch.Analysis['centre']` control point

        ```
            cp = surface.Points.GetControlPoint(0, cy.V / 2)
            cp.Weight = 1000
            for point in surface.Points:
                if point.X == 0 or point.Y == 0:
                    cp = ControlPoint(point.X, point.Y, point.Z, 1000)
                    surface.Points.SetControlPoint(0, cy.V / 2, cp)
        ```
        '''
        surface = NurbsSurface.CreateFromPoints(
            self.__points,
            self.UCount,
            self.VCount,
            self.UDegree,
            self.VDegree
        )

        self.Patch.Surfaces.append(surface)

    def JoinSurfaces(self, cy, *args):
        '''
        TODO Join Patch subdivisions
        Increase `doc.ModelAbsoluteTolerance` to maximise polysurface inclusion
        '''
        return
        # rs.JoinSurfaces(self.Patch.Surfaces[-2:])

    def Render(self, cy, *args):
        parent = rs.AddLayer('Surfaces')

        def cb(phase, patch, layer, ids):
            for i, surface in enumerate(patch.Surfaces):
                id = doc.Objects.AddSurface(surface)
                self.__rendered__(id)
                ids.append(id)
                rs.ObjectLayer(id, layer)

        Builder.Render(self, cb, cy, parent, *args)


__all__ = {
    1: PointCloudBuilder,
    2: MeshBuilder,
    3: CurveBuilder,
    4: SurfaceBuilder
}
