import System.Guid
import System.Enum
from math import pi
from scriptcontext import doc
from Rhino.Geometry import NurbsCurve, Curve, Brep, Vector3d, CurveKnotStyle
from Rhino.Geometry import Mesh
from Rhino.Geometry import Point3d


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
            # self.__rendered__(doc.Objects.AddPoint(Point3d(*point)))
            self.__rendered__(doc.Objects.AddPoint(point))


class MeshBuilder(Builder):
    __slots__ = ['Mesh', 'SubMesh']

    def __init__(self, cy):
        Builder.__init__(self, cy)
        self.Mesh = None
        self.SubMesh = None
        self.Meshes = []

    def __listeners__(self):
        return {
            'k2.on': [self.BuildMesh],
            'b.in': [self.BuildSubMesh],
            'k2.out': [self.JoinMesh]
        }

    def BuildMesh(self, cy, *args):
        # k1, k2, a = args

        self.Mesh = Mesh()

    def BuildSubMesh(self, cy, *args):
        k1, k2, a, b, point = args

        if a > cy.RngA[0]:
            if b > cy.RngB[0]:
                self.SubMesh = Mesh()

                for i in [
                    cy.PntCnt,
                    (cy.PntCnt - 1),
                    (cy.PntCnt - cy.SegCnt - 1),
                    (cy.PntCnt - cy.SegCnt)
                ]:
                    try:
                        # self.SubMesh.Vertices.Add(*cy.Points[i])
                        p = cy.Points[i - 1]  # account for 0 index
                        self.SubMesh.Vertices.Add(p.X, p.Y, p.Z)
                    except IndexError:
                        print 'Points[' + str(i) + '] out of range, ' + str(cy.PntCnt)

                self.SubMesh.Faces.AddFace(0, 1, 2, 3)
                # self.SubMesh.Normals.ComputeNormals()
                # self.SubMesh.Compact()
                self.Mesh.Append(self.SubMesh)

    def JoinMesh(self, cy, *args):
        '''
        TODO Assign to Segment
        '''
        self.Mesh.Weld(pi)
        self.Meshes.append(self.Mesh)  # cy.Meshes.append(self.Mesh)

    def Render(self, cy, *args):
        for mesh in self.Meshes:  # cy.Meshes:
            self.__rendered__(doc.Objects.AddMesh(mesh))


class CurveBuilder(Builder):
    def __init__(self, cy):
        Builder.__init__(self, cy)
        self.CalabiYau = cy


# TODO Move Curve behaviour into CurveBuilder and inherit
class SurfaceBuilder(Builder):
    '''
    Refer to [Curves Experimentation](https://bitbucket.org/snippets/kunst_dev/X894E8)

    Panelling tools or possible methods:
        rs.AddSrfControlPtGrid
        NurbsSurface.CreateNetworkSurface
        NetworkSrf
        Rhino.AddNetworkSrf
    '''

    __slots__ = []

    def __init__(self, cy):
        Builder.__init__(self, cy)
        self.C1 = None  # bound_start
        self.C2 = None  # bound_end
        self.C3 = None  # curve_outer
        self.C4 = None  # curve_inner
        self.SubCurves = None
        self.SubPoints = None
        self.Curves = []
        self.Breps = []
        self.U = []
        self.V = []

    def __listeners__(self):
        return {
            'k1.on': [self.Before],
            'a.in': [self.Build]
        }

    def Before(self, cy, *args):
        # k1, k2, a = args

        self.C1 = []
        self.C2 = []
        self.C3 = []
        self.C4 = []
        self.SubCurves = []
        self.SubPoints = []
        # self.V.append([])
        self.U.append([])

    def Build(self, cy, *args):
        '''
        TODO Ensure domain corner anchored to centre point
        TOOD Group points by surface domain
        TODO Group quad surface curves
        TODO Fit surface to domain points
        '''
        k1, k2, a, b, point = args

        self.SubPoints.append(point)

        u = self.U[-1]
        # self.V[-1]

        if a == cy.RngA[0]:
            self.C4.append(point)
            # u.append(point)
            # v.append(point)
        elif a == cy.RngA[-1]:
            self.C3.append(point)
            # u.append(point)
            # v.append(point)
        elif b == cy.RngB[0]:  # is this necessary?
            self.C1.append(point)
        elif b == cy.RngB[-1]:
            self.C2.append(point)

        # TODO do we need to be adding this to the front of the array arr.insert(0, val)
        if a == cy.RngA[0] or a == cy.RngA[-1]:
            u.append(point)
            # v.append(point)
            if b == cy.RngB[0]:
                self.C1.append(point)
            elif b == cy.RngB[-1]:
                self.C2.append(point)

    def After(self, cy, *args):
        print len(self.U[-1])
        # print len(self.V[-1])

        for curve in self.CreateInterpolatedCurves(*self.U):
            self.__rendered__(doc.Objects.AddCurve(curve))
            if rs.GetBoolean('Proceed',  ('Proceed?', 'No', 'Yes'), (True)) is None:
                break

        # rs.AddSrfPtGrid
        # u, v = len(self.CalabiYau.RngB), len(self.CalabiYau.RngB)
        # points = rs.coerce3dpointlist(self.SubPoints, True)
        # surf = NurbsSurface.CreateThroughPoints(points, u, v, 3, 3, False, False)
        # rs.AddSrfPtGrid([u, v], self.SubPoints)

        # self.CreateInterpolatedCurves()
        # for curve in self.CreateInterpolatedCurves(self.C1, self.C2, self.C3, self.C4):
        #     self.SubCurves.append(curve)
        #
        # self.Curves.append(self.SubCurves)

        # self.Breps.append(self.CreateBrep())

    def Render(self, *args):
        return
        # for point in self.CalabiYau.Points:
        #     self.__rendered__(doc.Objects.AddPoint(point))
        #
        # for curveGroup in self.Curves:
        #     for curve in curveGroup:
        #         self.__rendered__(doc.Objects.AddCurve(curve))
        #
        # for brep in self.Breps:
        #     try:
        #         self.__rendered__(doc.Objects.AddBrep(brep))
        #     except Exception:
        #         continue

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

    def CreateInterpolatedCurves(self, *args):
        '''
        '''
        return map(self.CreateInterpolatedCurve, args)

    def CreateBrep(self):
        '''
        Boundary Representation (Brep) from 4 curves

        TODO RssLib/rhinoscript/surface.py
            rs.AddSrfContourCrvs
            rs.AddSrfControlPtGrid
            rs.AddSrfPt
            rs.AddSrfPtGrid
        '''

        return Brep.CreateEdgeSurface(self.SubCurves)


__all__ = {
    1: PointCloudBuilder,
    2: MeshBuilder,
    3: CurveBuilder,
    4: SurfaceBuilder
}
