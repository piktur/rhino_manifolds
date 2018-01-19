import System.Guid
import System.Enum
from math import pi
from scriptcontext import doc
from Rhino.Geometry import NurbsCurve, NurbsSurface, Curve, Brep, Vector3d, CurveKnotStyle, Mesh, Point3d, ControlPoint
from Rhino.Collections import Point3dList, CurveList


class Builder:
    def __init__(self, cy):
        self.CalabiYau = cy

    def Build(self, *args, **kwargs):
        return

    def Render(self, *args, **kwargs):
        doc.Views.Redraw()

    def __rendered__(self, obj):
        '''
        Confirm `obj` present in document Guid
        '''
        if obj == System.Guid.Empty:
            raise Exception('RenderError')

        return True


class PointCloudBuilder(Builder):
    def __init__(self, *args):
        Builder.__init__(self, *args)

    def Render(self, cy, *args):
        for point in cy.Points:
            self.__rendered__(doc.Objects.AddPoint(point))


class MeshBuilder(Builder):
    __slots__ = ['Mesh', 'SubMesh', 'Meshes']

    def __init__(self, cy):
        Builder.__init__(self, cy)
        self.Mesh = None
        self.MeshCount = 0

    def __listeners__(self):
        return {
            'k2.on': [self.AddMesh],
            'b.on': [self.IncrementMeshCount],
            'b.in': [self.BuildMesh],
            'k2.out': [self.WeldMesh]
        }

    def AddMesh(self, cy, *args):
        # k1, k2, a = args

        cy.Patch.Mesh = Mesh()

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
                    cy.PointCount,
                    (cy.PointCount - 1),
                    (cy.PointCount - self.MeshCount - 1),
                    (cy.PointCount - self.MeshCount)
                ]:
                    try:   # account for 0 index
                        p = cy.Points[i - 1]
                        self.Mesh.Vertices.Add(p.X, p.Y, p.Z)
                    except IndexError:
                        print 'Points[' + str(i) + '] out of range, ' + str(cy.PointCount)

                self.Mesh.Faces.AddFace(0, 1, 2, 3)
                self.Mesh.Normals.ComputeNormals()
                # self.Mesh.Compact()
                cy.Patch.Append(self.Mesh)

    def WeldMesh(self, cy, *args):
        cy.Patch.Mesh.Weld(pi)

    def Render(self, cy, *args):
        for mesh in cy.Meshes:
            doc.Objects.AddMesh(mesh)
            # self.__rendered__(doc.Objects.AddMesh(mesh))

        doc.Views.Redraw()


class CurveBuilder(Builder):
    def __init__(self, cy):
        Builder.__init__(self, cy)

    def BuildSurfaceEdges(self, cy, *args):
        cy.Patch.Edges = map(
            self.CreateInterpolatedCurve,
            cy.Patch.C1,
            cy.Patch.C2,
            cy.Patch.C3,
            cy.Patch.C4
        )

    def PlotSurfaceEdges(self, cy, *args):
        k1, k2, a, b = args

        '''
        Use `Rhino.Command('ExtractEdges')`

        Example 1
        ```
            u = self.U[-1]
            # self.V[-1]

            if a == cy.RngU[0]:
                cy.Patch.C4.append(point)
                # u.append(point)
                # v.append(point)
            elif a == cy.RngU[-1]:
                cy.Patch.C3.append(point)
                # u.append(point)
                # v.append(point)
            elif b == cy.RngV[0]:  # is this necessary?
                cy.Patch.C1.append(point)
            elif b == cy.RngV[-1]:
                cy.Patch.C2.append(point)

            # TODO do we need to be adding this to the front of the array arr.insert(0, val)
            if a == cy.RngU[0] or a == cy.RngU[-1]:
                u.append(point)
                # v.append(point)
                if b == cy.RngV[0]:
                    cy.Patch.C1.append(point)
                elif b == cy.RngV[-1]:
                    cy.Patch.C2.append(point)
        ```

        Example 2
        ```
            cy.Patch.BPos += 1

            if a == cy.RngU[0]:
                cy.Patch.AddVCurve()

            if b == cy.RngV[0]:
                cy.Patch.AddCurve()
                cy.Patch.BPos = 0

            try:
                cy.Patch.GetCurve(-1).append(cy.Point)
            except AttributeError:
                pass

            try:
                if b == cy.RngV[-1]:
                    pass
                else:
                    # (cy.PatchCount * cy.Patch.BPos)
                    cy.Patch.GetVCurve(-cy.Patch.BPos).append(cy.Point)
            except AttributeError:
                pass

            # Collect all edge points
            if a == cy.RngU[0] or a == cy.RngU[-1]:
                cy.Patch.Edges.append(point)
            if b == cy.RngV[0] or b == cy.RngV[-1]:
                cy.Patch.Edges.append(cy.Point)

            # Collect points for each edge
            if a == cy.RngU[0]:
                cy.Patch.C4.append(cy.Point)
            elif a == cy.RngU[-1]:
                cy.Patch.C3.append(cy.Point)

            if a == cy.RngU[0] or a == cy.RngU[-1]:
                if b == cy.RngV[0]:
                    cy.Patch.C1.append(cy.Point)
                if b == cy.RngV[-1]:
                    cy.Patch.C2.append(cy.Point)
            elif b == cy.RngV[0]:
                cy.Patch.C1.append(cy.Point)
            elif b == cy.RngV[-1]:
                cy.Patch.C2.append(cy.Point)
        ```

        Example 3
        ```
            for phase in cy.Phases:
                k1, k2 = phase

                Crvs = CurveList()
                CrvA = []
                CrvB = []
                CrvC = []
                CrvD = []

                for a in RngU:
                    if a == RngU[0]:
                        CrvA = CreateInterpolatedCurve(map(lambda b: Point(k1, k2, a, b), RngV))
                    if a == RngU[-1]:
                        CrvC = CreateInterpolatedCurve(map(lambda b: Point(k1, k2, a, b), RngV))

                    for b in RngV:
                        if b == RngV[0]:
                            CrvB.append(Point(k1, k2, a, b))
                        if b == RngV[-1]:
                            CrvD.append(Point(k1, k2, a, b))


                Crvs.Add(CrvA)
                Crvs.Add(CrvB)
                Crvs.Add(CrvC)
                Crvs.Add(CrvD)

                surf, err = NurbsSurface.CreateNetworkSurface(
                    Crvs,  # IEnumerable<Curve> curves,
                    0,  # int continuity along edges, 0 = loose, 1 = pos, 2 = tan, 3 = curvature
                    0.0001,  # double edgeTolerance,
                    0.1,  # double interiorTolerance,
                    1.0  # double angleTolerance,
                )
        ```

        Example 4
        ```
            for a in RngU[0], RngU[len(RngU) / 2], RngU[-1]:
                for b in RngV:
                    point = Point(k1, k2, a, b)
                    rs.AddPoint(point)
            for a in RngU:
                for b in RngV[0], RngV[len(RngV) / 2], RngV[-1]:
                    point = Point(k1, k2, a, b)
                    rs.AddPoint(point)


            Crvs1 = CurveList()
            Crvs2 = CurveList()
            CrvA1 = []
            CrvA2 = []
            CrvB1 = []
            CrvB2 = []
            CrvC1 = []
            CrvC2 = []
            CrvD1 = []
            CrvD2 = []

            # CrvStart = []
            # CrvMid = []
            # CrvEnd = []

            for a in RngU:
                if a == RngU[0]:
                    CrvA1 = CreateInterpolatedCurve(map(lambda b: Point(k1, k2, a, b), RngV))
                if a == RngU[len(RngU) / 2]:
                    CrvC1 = CreateInterpolatedCurve(map(lambda b: Point(k1, k2, a, b), RngV))
                    CrvA2 = CrvC1
                if a == RngU[-1]:
                    CrvC2 = CreateInterpolatedCurve(map(lambda b: Point(k1, k2, a, b), RngV))

                for b in RngV:
                    if b == RngV[0]:
                        if len(CrvB1) <= 5: # <= (len(RngV) / 2)
                            CrvB1.append(Point(k1, k2, a, b))
                        if len(CrvB1) >= 5: # <= (len(RngV) / 2)
                            CrvB2.append(Point(k1, k2, a, b))
                    # if b == RngV[len(RngV) / 2]:
                    #     CrvMid.append(point)
                    if b == RngV[-1]:
                        if len(CrvD1) <= 5: # <= (len(RngV) / 2)
                            CrvD1.append(Point(k1, k2, a, b))
                        if len(CrvD1) >= 5: # <= (len(RngV) / 2)
                            CrvD2.append(Point(k1, k2, a, b))

            Crvs1.Add(CrvA1)
            Crvs1.Add(CrvB1)
            Crvs1.Add(CrvC1)
            Crvs1.Add(CrvD1)

            Crvs2.Add(CrvA2)
            Crvs2.Add(CrvB2)
            Crvs2.Add(CrvC2)
            Crvs2.Add(CrvD2)

            surf1, err = NurbsSurface.CreateNetworkSurface(
                Crvs1,  # IEnumerable<Curve> curves,
                0,  # int continuity along edges, 0 = loose, 1 = pos, 2 = tan, 3 = curvature
                0.0001,  # double edgeTolerance,
                0.1,  # double interiorTolerance,
                1.0  # double angleTolerance,
            )

            surf2, err = NurbsSurface.CreateNetworkSurface(
                Crvs2,  # IEnumerable<Curve> curves,
                0,  # int continuity along edges, 0 = loose, 1 = pos, 2 = tan, 3 = curvature
                0.0001,  # double edgeTolerance,
                0.1,  # double interiorTolerance,
                1.0  # double angleTolerance,
            )

            doc.Objects.AddSurface(surf1)
            doc.Objects.AddSurface(surf2)

            # for e in Crvs1:
            #     e = doc.Objects.AddCurve(e)
            #     rs.ObjectColor(e, 10)
        ```
        '''


# TODO Move Curve behaviour into CurveBuilder and inherit
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

    __slots__ = ['U', 'V', 'UDegree', 'VDegree', 'Points', 'UCount', 'VCount']

    def __init__(self, cy):
        Builder.__init__(self, cy)
        # Note: Polysurface created if U and V degrees differ.
        self.UDegree = 3
        self.VDegree = 3
        self.Points = None
        self.UCount = 0
        self.VCount = 0

    def __listeners__(self):
        return {
            'k2.on': [self.AddSurface],
            'a.on': [self.ResetV],
            'a.in': [],
            'b.in': [self.PlotSurface],  # self.PlotSurfaceEdges
            'b.out': [self.IncrementV],
            'a.out': [self.IncrementU, self.AddSurfaceSubdivision],
            'k2.out': [self.BuildSurface]  # self.BuildSurfaceEdges, self.BuildBrep
        }

    def AddSurface(self, *args):
        self.Points = Point3dList()
        self.ResetU()
        self.ResetV()

    def ResetU(self, *args):
        self.UCount = 0

    def ResetV(self, *args):
        self.VCount = 0

    def IncrementV(self, *args):
        self.VCount += 1

    def IncrementU(self, *args):
        self.UCount += 1

    def AddSurfaceSubdivision(self, cy, *args):
        k1, k2, a = args

        if a == cy.RngU[int(cy.U / 2)]:
            self.BuildSurface(cy, *args)  # Finalise current surface subdivision
            self.AddSurface(cy, *args)  # Begin next subdivision
            self.Points = Point3dList(cy.Points[-cy.U:])
            # self.IncrementV()
            self.IncrementU()

    def PlotSurface(self, cy, *args):
        k1, k2, a, b = args

        self.Points.Add(cy.Point)

    def BuildSurface(self, cy, *args):
        surface = NurbsSurface.CreateFromPoints(
            self.Points,
            self.UCount,
            self.VCount,
            self.UDegree,
            self.VDegree
        )

        # TODO Weight central control point
        # cp = surface.Points.GetControlPoint(0, cy.V / 2)
        # cp.Weight = 1000

        # for point in surface.Points:
        #     if point.X == 0 or point.Y == 0:
        #         cp = ControlPoint(point.X, point.Y, point.Z, 1000)

        # surface.Points.SetControlPoint(0, cy.V / 2, cp)

        # # cy.Patch.Surface = surface
        cy.Patch.Surfaces.append(surface)

    def BuildBrep(self, cy, *args):
        '''
        "Quadratic" Boundary Representation (Brep) from curves
        '''
        cy.Patch.Brep = Brep.CreateEdgeSurface(self.Patch.Edges)

    def BuildInterpolatedCurve(self, points):
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

    def Render(self, cy, *args):
        for subDivisions in cy.Surfaces():
            for surface in subDivisions:
                if surface: self.__rendered__(doc.Objects.AddSurface(surface))

        for curves in cy.Edges():
            for curve in curves:
                if curve: self.__rendered__(doc.Objects.AddCurve(curve))

        for brep in cy.Breps():
            if brep: self.__rendered__(doc.Objects.AddBrep(brep))


__all__ = {
    1: PointCloudBuilder,
    2: MeshBuilder,
    3: CurveBuilder,
    4: SurfaceBuilder
}
