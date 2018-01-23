import System.Guid
import System.Enum
from math import pi
from scriptcontext import doc
import rhinoscriptsyntax as rs
from Rhino.Geometry import Brep, ControlPoint, Curve, CurveKnotStyle, Mesh, NurbsCurve, NurbsSurface, Point3d, Vector3d
from Rhino.Collections import Point3dList, CurveList

from calabi_yau.calc import Calculate


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
        '__built__'
    ]

    def __init__(self, cy):
        self.CalabiYau = cy
        self.Points = Point3dList()
        self.Surfaces = []
        # self.Edges = []
        # self.Brep = None
        self.__built__ = False


class Builder:
    '''
    Attributes:
        CalabiYau : CalabiYau.Manifold
        Points : list<Rhino.Geometry.Point3d>
        Point : Rhino.Geometry.Point3d
        PointCount : int
            Cumulative position within `Plot3D` nested loop -- equiv to `len(self.Points)`
        Patches : list<Patch>
        Patch : Patch
        PatchCount : int
    '''
    __slots__ = ['CalabiYau',
                 'Points', 'Point', 'PointCount',
                 'Patches', 'Patch', 'PatchCount']

    def __init__(self, cy):
        self.CalabiYau = cy

        self.Points = []
        self.Point = None
        self.PointCount = 0

        self.Patches = []
        self.Patch = None
        self.PatchCount = 0

    def Build(self, *args, **kwargs):
        return

    def Surfaces(self):
        return map(lambda e: e.Surfaces, self.Patches)

    def Breps(self):
        return map(lambda e: e.Brep, self.Patches)

    def Edges(self):
        return map(lambda e: e.Edges, self.Patches)

    def Meshes(self):
        return map(lambda e: e.Mesh, self.Patches)

    def Render(self, *args, **kwargs):
        doc.Views.Redraw()

    def AddPatch(self, cy, *args):
        '''
        Add `self.n ** 2`th Patch
        '''
        self.Patch = Patch(cy)
        self.Patches.append(self.Patch)
        self.PatchCount += 1

        return self.Patch

    def BuildPoint(self, cy, *args):
        '''
        Calculate point coordinates and return Rhino.Geometry.Point3d
        '''
        coords = map(
            lambda i: (i * cy.Scale),
            Calculate(cy.n, cy.Alpha, *args)  # args[1:]
        )
        x, y = cy.Offset
        coords[0] = coords[0] + x
        coords[1] = coords[1] + y

        self.Point = Point3d(*coords)
        self.Points.Add(self.Point)
        self.Patch.Points.Add(self.Point)
        self.PointCount += 1

        return self.Point

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
        for point in self.Points:
            self.__rendered__(doc.Objects.AddPoint(point))


class MeshBuilder(Builder):
    __slots__ = Builder.__slots__ + ['Mesh']

    def __init__(self, cy):
        Builder.__init__(self, cy)
        self.Mesh = Mesh()
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

        self.Patch.Mesh = Mesh()

    def IncrementMeshCount(self, cy, *args):
        k1, k2, a, b = args

        if a == cy.RngU[0] and k2 == cy.RngK[0] and k1 == cy.RngK[0]:
            self.MeshCount += 1

    def BuildMesh(self, cy, *args):
        k1, k2, a, b = args

        if a > cy.RngU[0]:
            if b > cy.RngV[0]:
                self.Mesh = Mesh()

                for i in [
                    self.PointCount,
                    (self.PointCount - 1),
                    (self.PointCount - self.MeshCount - 1),
                    (self.PointCount - self.MeshCount)
                ]:
                    try:  # account for 0 index
                        p = self.Points[i - 1]
                        self.Mesh.Vertices.Add(p.X, p.Y, p.Z)
                    except IndexError:
                        print 'Points[' + str(i) + '] out of range, ' + str(self.PointCount)

                self.Mesh.Faces.AddFace(0, 1, 2, 3)
                self.Mesh.Normals.ComputeNormals()
                self.Mesh.Compact()
                self.Patch.Mesh.Append(self.Mesh)

    def WeldMesh(self, cy, *args):
        self.Patch.Mesh.Weld(pi)

    def Render(self, cy, *args):
        for mesh in self.Meshes():
            self.__rendered__(doc.Objects.AddMesh(mesh))

        doc.Views.Redraw()


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
        self.A = []
        self.B = []
        self.C = []
        self.D = []

        self.A1 = []
        self.B1 = []
        self.C1 = []
        self.D1 = []

        self.A2 = []
        self.B2 = []
        self.C2 = []
        self.D2 = []

    def PlotEdges(self, cy, *args):
        '''
        [#10](https://bitbucket.org/kunst_dev/snippets/issues/10/curve-generation)
        '''
        k1, k2, a, b = args

        if a == cy.RngU[0]:
            self.A.append(self.Point)
            self.A1.append(self.Point)
        if a == cy.RngU[cy.CentreU]:
            self.C1.append(self.Point)
            self.C2.append(self.Point)
        if a == cy.RngU[-1]:
            self.C.append(self.Point)
            self.A2.append(self.Point)

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

        for points in (self.A, self.B, self.C, self.D):
            Edges.Add(self.BuildInterpolatedCurve(points))

        # Sub-dvisions
        for points in (self.A1, self.B1, self.C1, self.D1):
            Edges1.Add(self.BuildInterpolatedCurve(points))

        for points in (self.A2, self.B2, self.C2, self.D2):
            Edges2.Add(self.BuildInterpolatedCurve(points))

        self.Patch.Edges = [Edges, Edges1, Edges2]

    def BuildInterpolatedCurve(self, points):
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

        curve = Curve.CreateInterpolatedCurve(points, degree, knotstyle, start_tangent, end_tangent)

        if curve:
            return curve

        raise Exception('Unable to CreateInterpolatedCurve')

    def Render(self, cy, *args):
        for patch in self.Edges():
            Edges, Edges1, Edges2 = patch

            for edgeGroup in Edges1, Edges2:
                for curve in edgeGroup:
                    self.__rendered__(doc.Objects.AddCurve(curve))

                # Create Boundary Representation
                # self.Patch.Brep = Brep.CreateEdgeSurface(edgeGroup)
                # self.__rendered__(doc.Objects.AddBrep(self.Patch.Brep))

                # Create Nurbs Surface
                # surface, err = NurbsSurface.CreateNetworkSurface(
                #     edgeGroup,
                #     1,
                #     0.1,
                #     0.1,
                #     1.0
                # )
                # self.__rendered__(doc.Objects.AddSurface(surface))


class SurfaceBuilder(Builder):
    '''
    TODO
        * Optimise curvature degree and U/V count.


    Build "quadratic" surfaces and/or curve objects per patch.
    Refer to [Curves Experimentation](https://bitbucket.org/snippets/kunst_dev/X894E8)

    Panelling tools or possible methods:
        rs.AddSrfControlPtGrid
        NurbsSurface.CreateNetworkSurface
        NetworkSrf
        Rhino.AddNetworkSrf
    '''
    __slots__ = Builder.__slots__ + ['UDegree', 'VDegree', '__points', 'UCount', 'VCount']

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
        listeners['a.out'].extend([self.IncrementUCount, self.AddSurfaceSubdivision])
        listeners['k2.out'].extend([self.BuildSurface, self.JoinSurfaces])  # self.BuildEdgeSurface

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

        if a == cy.RngU[cy.CentreU]:
            self.BuildSurface(cy, *args)  # Finalise current surface subdivision
            self.AddSurface(cy, *args)  # Begin next subdivision
            self.__points = Point3dList(self.Points[-cy.U:])
            self.IncrementUCount()

    def PlotSurface(self, cy, *args):
        k1, k2, a, b = args

        self.__points.Add(self.Point)

    def BuildSurface(self, cy, *args):
        '''
        TODO Add `Weight` to central control point

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

    def BuildEdgeSurface(self, edges, *args):
        surface, err = NurbsSurface.CreateNetworkSurface(
            edges,  # IEnumerable<Curve> curves,
            1,  # int continuity along edges, 0 = loose, 1 = pos, 2 = tan, 3 = curvature
            0.001,  # double edgeTolerance,
            0.001,  # double interiorTolerance,
            0.001  # double angleTolerance,
        )

        self.Patch.Surfaces.append(surface)

    def JoinSurfaces(self, cy, *args):
        '''
        TODO Join Patch subdivisions
        '''
        return
        # rs.JoinSurfaces(self.Patch.Surfaces[-2:])

    def Render(self, cy, *args):
        for subDivisions in self.Surfaces():
            for surface in subDivisions:
                if surface:
                    self.__rendered__(doc.Objects.AddSurface(surface))


__all__ = {
    1: PointCloudBuilder,
    2: MeshBuilder,
    3: CurveBuilder,
    4: SurfaceBuilder
}
