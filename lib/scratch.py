import os
import sys
import importlib
import cmath
from math import cos, sin, pi, fabs
import rhinoscriptsyntax as rs
import scriptcontext
from scriptcontext import doc, errorhandler
import Rhino.Geometry.NurbsSurface as NurbsSurface
import Rhino.Geometry.Point3d as Point3d
import Rhino.Geometry.Mesh as Mesh
import Rhino.Geometry.BrepFace as BrepFace
import Rhino.Geometry.Brep as Brep
import Rhino.Geometry.Intersect as Intersect
import Rhino.Geometry.Curve as Curve
import Rhino.Geometry.Transform as Transform
from Rhino.Collections import Point3dList, CurveList
import System.Guid
import System.Drawing.Color as Color
# import Grasshopper
# import GhPython
from Rhino.RhinoApp import RunScript
import Rhino.Geometry.Surface as Surface

import itertools


# TODO
# Brep.Reverse()
# Brep.Transpose()
# Brep.Direction()
# rs.Command('MakeUniform')
# rs.Command('MakeUniformUV')
# Surface.Evaluate()
# Surface.CurvatureAt()
# Surface.Fit()
# Surface.FrameAt()
# Surface.GetSurfaceSize()
# Surface.GetUserStrings()
# Surface.IsoCurve()
# print(Surface.ShortPath())
# print(Surface.UserData())


builder = scriptcontext.sticky['builder']
log = open('./log.txt', 'w')


# http://www.grasshopper3d.com/profiles/blogs/reverse-and-swap-u-and-v-directions-of-surface
def Dir(srf, reverseU=False, reverseV=False, swapUV=False):
    '''
    Equivalent to Rhino's `Dir` command

    Grasshopper Lunchbox example
    def ReverseSrfDirection(srf, direction=0):
        if direction == 0:
            return srf
        elif direction == 1:
            srf.Reverse(0)
        elif direction == 2:
            srf.Reverse(1)
        elif direction == 3:  # 'UV'
            srf.Transpose()

        return srf
    '''
    if reverseU:
        minU, maxU = srf.Domain(0)
        interval0 = Rhino.Geometry.Interval(-maxU, -minU)
        srf.SetDomain(0, interval0)
        srf = srf.Reverse(0)

    if reverseV:
        minV, maxV = srf.Domain(1)
        interval1 = Rhino.Geometry.Interval(-maxV, -minV)
        srf.SetDomain(1, interval1)
        srf = srf.Reverse(1)

    if swapUV:
        srf = srf.Transpose()

    anchor = srf.PointAt(0.0, 0.0)
    maxU = srf.PointAt(0.5, 0.0)
    maxV = srf.PointAt(0.0, 0.5)
    uVector = maxU - anchor
    vVector = maxV - anchor

    return anchor, uVector, vVector, srf


def PlotStartingPoints():
    rs.AddLayer('Sorted', Color.Red)
    rs.AddLayer('UnSorted', Color.Violet)

    startingPoints = Point3dList()
    for i, srf in enumerate(builder.Surfaces['Div1']):
        startingPoints.Add(srf.Points.GetControlPoint(0, 0).Location)

    sorted = rs.SortPoints(startingPoints)

    id = rs.AddCurve(sorted, 1)
    rs.ObjectLayer(id, 'Sorted')

    id = rs.AddCurve(startingPoints, 1)
    rs.ObjectLayer(id, 'UnSorted')


def DivideOuterBordersAndExtractIsoCurveThroughDivision():
    borders = Curve.JoinCurves(builder.Outer)

    # points = curve.DivideEquidistant(10)
    curve = borders[0]
    divisions = curve.DivideByCount(10, True)
    points = [curve.PointAt(t) for t in divisions]

    done = []
    DivU = Point3dList()

    for i, srf in enumerate(builder.Surfaces['Div1']):
        for point in points:
            brep = Brep.TryConvertBrep(srf)
            result, parameter = builder.ClosestPoint(brep, point, 0.1)

            if result:
                done.append(srf)
                _u, _v = builder.ExtractIsoCurve(srf, parameter, 0)

                for curve in _u:
                    doc.Objects.AddCurve(curve)
                    rs.AddPoint(curve.PointAtEnd)
                    DivU.Add(curve.PointAtEnd)


def Normals():
    for i, srf in enumerate(builder.Surfaces['Div1']):
        direction = srf.NormalAt(0, 0)
        rs.AddPoint(direction)

        # if srf.OrientationIsReversed:
        #     direction.Reverse()
        #
        # "Surface normal at uv(0,0) = ({0:f},{1:f},{2:f})"

        # log.write(str(direction.X))


def Analyse(srf):
    _ = {}
    _['U'] = srf.SpanCount(0)  # + 3
    _['V'] = srf.SpanCount(1)  # + 3
    _['minU'], _['maxU'] = srf.Domain(1)
    _['minV'], _['maxV'] = srf.Domain(0)
    _['stepU'] = fabs(_['maxU'] - _['minU']) / float(_['U'] - 1)  # * 2.0  # _['maxU'] / 28.0
    _['stepV'] = fabs(_['maxV'] - _['minV']) / float(_['V'] - 1)  # * 2.0  # _['maxV'] / 55.0

    return _


def ExtractIsoCurvesFromBaseCurveDivisions(srf):
    _ = Analyse(srf)

    if i == 0:
        UDiv = Point3dList()
        VDiv = Point3dList()

        # base = Point3dList()
        # for u in range(srf.Points.CountU):
        #     base.Add(srf.Points.GetControlPoint(u, 0).Location)
        # Then create the curve from base points list

        _u, _v = builder.ExtractIsoCurve(srf, (0, 0), 1)
        baseCurve = _v[0]

        # UDiv = baseCurve.DivideByLength(2.5, True)  # Curve Parameters
        # points = [baseCurve.PointAt(t) for t in UDiv]
        # for parameter in divisions:
        #     _u, _v = builder.ExtractIsoCurve(srf, (None, parameter), 0)
        #     for curve in _u:
        #         doc.Objects.AddCurve(curve)
        #         UDiv.Add(curve.PointAtEnd)

        points = baseCurve.DivideEquidistant(10)

        for point in points:
            brep = Brep.TryConvertBrep(srf)
            result, parameter = builder.ClosestPoint(brep, point, 0.1)
            _u, _v = builder.ExtractIsoCurve(srf, parameter, 0)

            for curve in _u:
                doc.Objects.AddCurve(curve)
                UDiv.Add(curve.PointAtEnd)

    if i == 1:
        for point in UDiv:
            brep = Brep.TryConvertBrep(srf)
            result, parameter = builder.ClosestPoint(brep, point, 0.1)
            u, v = parameter
            _u, _v = builder.ExtractIsoCurve(srf, (u, v), 0)
            for curve in _u:
                doc.Objects.AddCurve(curve)


def ExtractIsoCurvesForPair(srf, n):
    _ = Analyse(srf)
    UDiv = None
    VDiv = None

    if n == 0:
        UDiv = Point3dList()
        VDiv = Point3dList()

        for u in rs.frange(_['minU'], _['maxU'], _['stepU']):
            _u, _v = builder.ExtractIsoCurve(srf, (u, None), 1)

            for curve in _v:
                # rs.AddPoint(curve.PointAtEnd)
                VDiv.Add(curve.PointAtEnd)
                doc.Objects.AddCurve(curve)

        for v in rs.frange(_['minV'], _['maxV'], _['stepV']):
            _u, _v = builder.ExtractIsoCurve(srf, (None, v), 1)

            for curve in _u:
                # rs.AddPoint(curve.PointAtEnd)
                UDiv.Add(curve.PointAtEnd)
                doc.Objects.AddCurve(curve)

    if n == 1:
        for point in UDiv:
            brep = Brep.TryConvertBrep(srf)
            result, parameter = builder.ClosestPoint(brep, point, 0.1)
            _u, _v = builder.ExtractIsoCurve(srf, parameter, 1)

            for curve in _v:
                doc.Objects.AddCurve(curve)

        for point in VDiv:
            brep = Brep.TryConvertBrep(srf)
            result, parameter = builder.ClosestPoint(brep, point, 0.1)
            _u, _v = builder.ExtractIsoCurve(srf, parameter, 0)

            for curve in _u:
                doc.Objects.AddCurve(curve)


def ExtractIsoCurvesByDividingSurfaceDomain(srf):
    # NURBS geometry parameter space divisions are not equivalent to length.
    # https://ieatbugsforbreakfast.wordpress.com/2013/09/27/curve-parameter-space/
    _ = Analyse(srf)
    U = CurveList()
    V = CurveList()

    for parameter in rs.frange(_['minV'], _['maxV'], _['stepV']):
        _u, _v = builder.ExtractIsoCurve(srf, (parameter, None), 1)
        for curve in _v:
            V.Add(curve)

    # for parameter in rs.frange(_['minU'], _['maxU'], _['stepU']):
    #     _u, _v = builder.ExtractIsoCurve(srf, (parameter, None), 1)
    #     for curve in _v:
    #         V.Add(curve)

    return U, V


def ExtractIsoCurvesAtSrfControlPoints(srf):
    U = CurveList()
    V = CurveList()

    for u in range(0, srf.Points.CountU, 2):
        p = srf.Points.GetControlPoint(u, 0).Location
        result, _u, _v = srf.ClosestPoint(p)
        _u, _v = builder.ExtractIsoCurve(srf, (_u, _v), 1)

        for curve in _v:
            V.Add(curve)

    for v in range(0, srf.Points.CountV, 2):
        p = srf.Points.GetControlPoint(0, v).Location
        result, _u, _v = srf.ClosestPoint(p)
        _u, _v = builder.ExtractIsoCurve(srf, (_u, _v), 0)

        for curve in _u:
            U.Add(curve)

    return U, V


def SeperateUVFromExtractWireframe(srf):
    # Run `ExtractWireframe`
    # Iterate the curves
    #   Run Dir() to find separate U from V curves
    # Then Add/Remove as required
    pass

    # Maybe just generate the densest wireframe and then reduce
    for i in range(1, 5, 1):
        ids = builder.Rendered['PolySurface']['Div1']
        layer = rs.AddLayer('::'.join(('Wireframe', str(i))))

        U = CurveList()
        V = CurveList()

        for id in ids:
            obj = rs.coercerhinoobject(id, True, True)
            obj.Attributes.WireDensity = i
            obj.CommitChanges()

        rs.SelectObjects(ids)
        rs.Command(
            '_MakeUniform '
            + '_ExtractWireframe '
            + 'OutputLayer=Input '
            + 'GroupOutput=Yes '
            + '_Enter '
        )

        curves = CurveList()
        for id in rs.LastCreatedObjects(True):
            curve = rs.coercecurve(id)

            # TODO Separate by direction
            direction = curve.NormalAt(0, 0)
            N = False
            E = False
            S = False
            W = False

            if direction.X > 0:
                U.Add(curve)
                V.Add(curve)

            if direction.Y > 0:
                U.Add(curve)
                V.Add(curve)

            if direction.Z > 0:
                U.Add(curve)
                V.Add(curve)

        for e in ('U', 'V'):
            curves = eval(e)
            layer = rs.AddLayer('::'.join(('Wireframe', str(i), e)))

            for curve in Curve.JoinCurves(curves, 0.1, False):
                rs.ObjectLayer(id, layer)


def RenderCurves(curves):
    for curve in curves:
        doc.Objects.AddCurve(curve)


for n in range(2):
    srf = builder.Surfaces['Div1'][n]

    # REPORT :
    #   * Matches Wireframe
    #   * Need to unify surface directions in order to decrease/increase wire count
    #   * Whilst `MakeUniform` improves wireframe apperance it doesn't seem to affect control points
    # U, V = ExtractIsoCurvesAtSrfControlPoints(srf)
    # RenderCurves(U)
    # RenderCurves(V)

    # REPORT :
    #   * Yeah don't divide surface domain as if it were length
    # U, V = ExtractIsoCurvesByDividingSurfaceDomain(srf)
    # RenderCurves(U)
    # RenderCurves(V)

# REPORT :
#   *
# SeperateUVFromExtractWireframe()


patch = builder.Patches[0]  # for patch in builder.Patches:
for n, srf in enumerate(patch.Surfaces['Div1']):
    pass
    # REPORT :
    #   *
    # ExtractIsoCurvesForPair(srf, n)

    # REPORT :
    #   *
    # ExtractIsoCurvesFromBaseCurveDivisions(srf)



def Make2d():
    '''
    THIS WORKS!!!
    Only problem is I don't know how to ammend the layers.



    ROTTING OOZE
    Especially in 2Dimension CY the seam bulges in all sorts of ugly ways. Curves interpolated over it are ripe. `MergeSrf`seems to improve the situation.
    Maybe we could run a MergeSrf on all SurfaceCombinations. Bear in mind it will fuck the junction up.

    TODO
    - Fix intersections, we don't want the overlaps
    - Are Brep Curve and Surface combinations actually correct, do we need to use object ids instesad.
    - Finish Make2d
    '''
    # TODO staged Make2d
    # Run make2d numerous times selecting only a small number of curves at a time. This seems to yield better output than throwing everythin at it at once. Silhouette edges are especially bad.
    # Low < 0.1 tolerance works best.
    builder = scriptcontext.sticky['builder']

    rs.SelectObjects(
        # *self.Rendered['IsoCurves']['U'], # Do a subset of either U or V at a time
        builder.Rendered['Surfaces']['Div1'] #  or *self.Rendered['PolySurface']['Div1']
    )

    RunScript(
        '-Make2D DrawingLayout=CurrentView '
        + 'ShowTangentEdges=No '
        + 'CreateHiddenLines=No '
        + 'MaintainSourceLayers=Yes '
        + 'Enter '
        + '-Invert ',
        # + 'Hide '
        # + 'SetView World Top ZE SelNone'
        True
    )

    # TODO
    #   Major improvement
    #   We may want to step through each problem curve with the user getting confirmation before performing the trim.
    # Find all curves with a gap larger than tolerance
    # Say if a curve ends in the middle of nowhere
    # does the meet another. it should so if it doesn't
    #   then find the nearest curve and trim from end to intersection

# Make2d()

# rs.RestoreNamedView(view)

# if __name__ == '__main__':
#     objs = rs.GetObjects('Select Curves', rs.filter.curve)
#     curves = []
#     for obj in objs:
#         curves.append(rs.coercecurve(obj))
#
#     result = []
#     for a in curves:
#         for b in curves:
#             if b != a:
#                 # rs.CurveCurveIntersection(a, b)
#                 result.append(Intersect.Intersection.CurveCurve(a, b, doc.ModelAbsoluteTolerance, 0.1))
#     print result

# # Attempt to draw a curve through ordered points
# pointsList = Eq.Result['Theta0']
#
# # Example 1
# curve = Builder.BuildInterpolatedCurve(pointsList)
#
# # Example 2
# points = Point3d.SortAndCullPointList(pointsList, doc.ModelAbsoluteTolerance)
# curve = Builder.BuildInterpolatedCurve(points)
#
# # Example 3
# points = rs.SortPoints(pointsList.ToArray(), True, 5)
# curve = Builder.BuildInterpolatedCurve(points)
#
# curve = Builder.BuildInterpolatedCurve(pointsList)
# doc.Objects.AddCurve(curve)
# doc.Views.Redraw()
#
# PolySrf = rs.ObjectsByLayer('PolySrf')[0]
# box = rs.BoundingBox(PolySrf)
# for i, p in enumerate(box):
#     doc.Objects.AddTextDot(str(i), p)
#
#
# plane = rs.PlaneFromPoints(box[7], box[6], box[2])
# xform = rs.XformPlanarProjection(plane)
# rs.TransformObjects(PolySrf, xform, True)

# rs.PlaneFromPoints(origin, x, y)
# plane = rhutil.coerceplane(plane, True)
# Transform.PlanarProjection(plane)


# curves = CurveList()
# for curve in rs.ObjectsByLayer('Layer 01'):
#     curves.Add(rs.coerceline(curve))

# curve_ids = map(lambda e: e.Id.ToString(), rs.ObjectsByLayer('Layer 01'))


# breps = []
# surfaces = []
# tolerance = doc.ModelAbsoluteTolerance
# for id in rs.ObjectsByLayer('Default'):  # rs.ObjectsByType(rs.filter.surface)
#     breps.append((id, rs.coercebrep(id, True)))
#
# for id in rs.ObjectsByLayer('Default'):  # rs.ObjectsByType(rs.filter.surface)
#     surfaces.append((id, rs.coercesurface(id, True)))
#
# # 1. Join Patches into PolySrf
# # 2. DupBorder on PolySrf
# # 3. Group patches where edge intersects border
#
# # for i, curve_id in enumerate(rs.ObjectsByLayer('Border::Outer')):  # rs.ObjectsByType(rs.filter.curve):
# curve_id = rs.ObjectsByLayer('Border::Outer')[0]
# group = rs.AddGroup()  # ('Sect' + str(i))
# arr = []
# curve = rs.coercecurve(curve_id, True)
#
# for obj in surfaces:
#     surface_id, surface = obj
#     intersections = Intersect.Intersection.CurveSurface(curve, surface, tolerance, tolerance)
#     # result = rs.CurveSurfaceIntersection(curve, surface)
#
#     for intersection in intersections:
#         for i in xrange(intersections.Count):
#             if intersections[i].IsOverlap or intersections[i].IsPoint:
#                 arr.append(surface_id)
#
# # for obj in breps:
# #     brep_id, brep = obj
# #
# #     # result = rs.CurveBrepIntersect(curve_id, brep_id)
# #     rc, out_curves, out_points = Intersect.Intersection.CurveBrep(curve, brep, tolerance)
# #     if len(out_curves) > 0:
# #         arr.append(brep_id)
#
# rs.AddObjectsToGroup(arr, group)
# doc.Views.Redraw()
# # rs.JoinSurfaces(arr, True)

# rs.SplitBrep(brep, curve, False)
# curves, points = result
# for curve in curves:
#     doc.Objects.AddCurve(rs.coercecurve(curve))

# curves = CurveList()
# for curve in rs.ObjectsByLayer('2D::Inter::visible::outline5'):
#     curve = rs.coercecurve(curve, True)
#     curves.Add(curve)
#
# Curve.JoinCurves(curves, 2.1 * tolerance, True)
# doc.Objects.AddCurve(curve)


    # for curve in rs.ObjectsByLayer('Layer 01'):  # rs.ObjectsByType(rs.filter.curve):
        # result = rs.CurveBrepIntersect(curve, surface)
        # result = rs.CurveSurfaceIntersection(curve, surface)
        # if result:
        #     curves = CurveList()
        #     curves.Add(rs.coerceline(curve))
        #     # rs.coercebrep(surface, True)
        #     # BrepFace.Split(curve, doc.ModelAbsoluteTolerance)
        #     rs.coercesurface(surface).Split(curves, doc.ModelAbsoluteTolerance)

        # rs.SplitBrep(surface, curve, False)
        # curves, points = result
        # for curve in curves:
        #     doc.Objects.AddCurve(rs.coercecurve(curve))


    # rs.Command('Split ' + surface.Id.ToString(), + ' ,'.join(curve_ids))

    # surface = rs.coercesurface(surface)

    # result = surface.Split(curves, doc.ModelAbsoluteTolerance)

    # doc.Objects.AddBrep(result)


# doc.Views.Redraw()


# import Rhino
# Rhino.RhinoDoc
# # view = rs.__viewhelper('Perspective')
# viewport = doc.Views.ActiveView.ActiveViewport
# viewport.ChangeToParallelProjection(True)
#
# arrObjects = rs.GetObjects("Select curves to draw", 4, True, True)
# strView = rs.CurrentView
# if rs.IsViewPerspective(strView):
#     print Rhino.__dict__
#     rs.XformPlanarProjection(cplane)
#     arrXform = Rhino.ViewProjectionXform(strView)
#     # Rhino.TransformObjects(arrObjects, arrXform, True)

# import calabi_yau

# import System.Enum
#
# print System.Enum.__dict__

# Returns absolute path for module
# print rs.__file__

# doc.Views.ActiveView.ActiveViewport
# rhino_object = rhutil.coercerhinoobject(surface_id, True, True)
# layerNames = rs.LayerNames()
#
# for object in selected:
#     object.Attributes.LayerIndex = layer
#     object.CommitChanges()
#
# doc.Objects.ModifyAttributes(id, )
# print obj.Attributes
#
# rs.EnableRedraw(False)
