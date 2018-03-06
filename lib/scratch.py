import os
import sys
import importlib
import cmath
from math import cos, sin, pi, fabs
import rhinoscriptsyntax as rs
import scriptcontext
from scriptcontext import doc, errorhandler
import Rhino.Geometry.NurbsSurface as NurbsSurface
import Rhino.Geometry.NurbsCurve as NurbsCurve
import Rhino.Geometry.Point3d as Point3d
import Rhino.Geometry.Point2d as Point2d
import Rhino.Geometry.Mesh as Mesh
import Rhino.Geometry.BrepFace as BrepFace
import Rhino.Geometry.Brep as Brep
import Rhino.Geometry.Intersect as Intersect
import Rhino.Geometry.Curve as Curve
import Rhino.Geometry.Interval as Interval
import Rhino.Geometry.Sphere as Sphere
import Rhino.Geometry.Transform as Transform
import Rhino.Geometry.Vector2d as Vector2d
from Rhino.Collections import Point3dList, CurveList, RhinoList
import Rhino.Geometry as Geometry
import System.Guid
import System.Drawing.Color as Color
# import Grasshopper
# import GhPython
from Rhino.RhinoApp import RunScript
import Rhino.Geometry.Surface as Surface

import itertools

from Rhino.Geometry import Interval


#   Refer to Downloads/Divide_surface_rectangles.ghx for alternate isocurve generation methods.
def ExtractIsoCurves(srf=None, div=None):
    # result, maxU, maxV = srf.GetSurfaceSize()
    # U = round(maxU / 2.0, 0)
    # V = round(maxV / 2.0, 0)
    # stepU = 1.0 / (U)
    # stepV = 1.0 / (V)
    # rngU = rs.frange(0.0, 1.0, stepU)
    # rngU.reverse()
    # rngV = rs.frange(0.0, 1.0, stepV)

    interval = srf.Domain(1)
    min = interval.Min
    max = interval.Max

    curvesU = CurveList()
    count = 1 * srf.SpanCount(1)
    countU = 0

    while countU <= count:
        t = (min + (countU / count)) * (max - min)
        curve = srf.IsoCurve(0, t)
        doc.Objects.AddCurve(curve)
        curvesU.Add(curve)
        countU += 1

    interval = srf.Domain(0)
    min = interval.Min
    max = interval.Max

    curvesV = CurveList()
    count = 1 * srf.SpanCount(0)
    countV = 0

    while countV <= count:
        t = (min + (countV / count)) * (max - min)
        curve = srf.IsoCurve(1, t)
        doc.Objects.AddCurve(curve)
        curvesV.Add(curve)
        countV += 1

    # points = []
    # for y in rngV:
    #     x = None
    #     if len(rngU) > 0:
    #         x = rngU.pop()
    #     else:
    #         x = 1.0
    #     # Point2d()
    #     points.append((x, y))

    # for (x, y) in points:
    #     curveX = srf.IsoCurve(1, y)
    #     # y = srf.IsoCurve(1, y)
    #     doc.Objects.AddCurve(curveX)
    #     # doc.Objects.AddCurve(x)


def UVGrid(srf, U, V, points, normals, inc, isBrep):
    countU = 0

    while countU <= U:
        intervalU = srf.Domain(0)
        u = intervalU.ParameterAt(countU / U)

        countV = 0
        while countV <= V:
            intervalV = srf.Domain(1)
            v = intervalV.ParameterAt(countV / V)
            point = srf.PointAt(u, v)
            points.Add(point)

            normal = srf.NormalAt(u, v)
            normals.append(normal)

            if isBrep:
                inc.append(srf.IsPointOnFace(u, v))
            else:
                inc.append(True)

            countV += 1
        countU += 1

    return points, normals, inc


def chunk(arr, size):
    '''
    Yield successive chunks of `size` from `list`.
    '''
    for i in range(0, len(arr), size):
        yield arr[i:i + size]


def UVGridEqualized(srf, U, V, points, normals, inc, isBrep):
    isoCurvesU = BuildUIsoCurves(srf, 1.0)
    # isoCurvesV = [Point3dList() for n in range(V)]

    countU = 0
    while countU <= U:
        curve = FitEqualizedIsoCurve(srf, isoCurvesU, countU / U)
        if curve:
            countV = 0
            while countV <= V:
                result, parameter = curve.NormalizedLengthParameter(countV / V)
                if result:
                    point = curve.PointAt(parameter)

                    result, u, v = srf.ClosestPoint(point)
                    if result:
                        point = srf.PointAt(u, v)
                        points.Add(point)

                        normal = srf.NormalAt(u, v)
                        normals.append(normal)

                        # isoCurvesV[countU - 1].Add(point)

                        if isBrep:
                            inc.append(srf.IsPointOnFace(u, v))
                        else:
                            inc.append(True)
                countV += 1
        countU += 1

    # for points in isoCurvesV:
    #     start = points.First
    #     end = points.Last
    #     curve = srf.InterpolatedCurveOnSurface((start, end), 0.1)
    #     doc.Objects.AddCurve(curve)

    isoCurvesV = BuildVIsoCurves(srf, 1.0)

    countV = 0
    while countV <= V:
        curve = FitEqualizedIsoCurve(srf, isoCurvesV, countV / V)
        if curve:
            doc.Objects.AddCurve(curve)

        countV += 1

def BuildUIsoCurves(srf, n):
    interval = srf.Domain(1)
    min = interval.Min
    max = interval.Max

    curves = CurveList()
    count = n * srf.SpanCount(1)
    countU = 0

    while countU <= count:
        t = (min + (countU / count)) * (max - min)
        curves.Add(srf.IsoCurve(0, t))
        countU += 1

    return curves

def BuildVIsoCurves(srf, n):
    interval = srf.Domain(0)
    min = interval.Min
    max = interval.Max

    curves = CurveList()
    count = n * srf.SpanCount(0)
    countV = 0

    while countV <= count:
        t = (min + (countV / count)) * (max - min)
        curves.Add(srf.IsoCurve(1, t))
        countV += 1

    return curves

def FitEqualizedIsoCurve(srf, curves, div):
    maxDistance = doc.ModelAbsoluteTolerance
    points = []
    count = curves.Count - 1  # 0 offset:
    i = 0

    while i <= count:
        point = PointAtRatio(srf, curves[i], div)
        result, u, v = srf.ClosestPoint(point)
        if result:
            points.append((u, v))
            # points.append(srf.PointAt(u, v))
        i += 1

    for point in points:
        log.write('\n' + str(point))

    return srf.InterpolatedCurveOnSurfaceUV(points, 0.1)
    # return srf.InterpolatedCurveOnSurface(points[0::count], 0.1)

def PointAtRatio(srf, curve, div):
    result, parameter = curve.NormalizedLengthParameter(div)
    if result:
        return curve.PointAt(parameter)

def BuildIsoCurves(srf, U, V, trimAware=True, euqalizeSpanLength=False):
    tolerance = doc.ModelAbsoluteTolerance
    quad = range(4)
    combinations = zip(quad, (1, 2, 3, 0))
    isSurface = isinstance(srf, Surface)
    isBrepFace = isinstance(srf, BrepFace)
    brep = Brep.TryConvertBrep(srf).Faces[0]
    points = Point3dList()
    normals = []
    inc = []

    if euqalizeSpanLength:
        UVGridEqualized(brep, U, V, points, normals, inc, isBrepFace)
    else:
        UVGrid(brep, U, V, points, normals, inc, isBrepFace)

    def BuildMesh():
        maxU = U - 1  # zero offset
        count = points.Count - 1
        countU = 0
        i = 0
        mesh = Mesh()

        while i <= count:
            mesh.Vertices.Add(points[i])
            mesh.Normals.Add(normals[i])
            i += 1

        while countU <= maxU:
            maxV = V - 1  # zero offset
            countV = 0

            while countV <= maxV:
                # Here we build our GRID
                i0 = (countU * (V + 1) + countV)
                i1 = (i0 + V + 1)
                i2 = (i1 + 1)
                i3 = (i0 + 1)

                if trimAware:
                    if inc[i0] or inc[i1] or (inc[i2] or inc[i3]):
                        mesh.Faces.AddFace(i0, i1, i2, i3)
                elif inc[i0] and inc[i1] and (inc[i2] and inc[i3]):
                    mesh.Faces.AddFace(i0, i1, i2, i3)

                countV += 1
            countU += 1

        mesh.Vertices.CullUnused()

        return mesh

    def BuildSubSurfaces():
        maxU = U - 1  # zero offset
        count = points.Count - 1
        countU = 0
        i = 0

        while countU <= maxU:
            maxV = V - 1  # zero offset
            countV = 0

            while countV <= maxV:
                i0 = countU * (V + 1) + countV
                i1 = i0 + V + 1
                i2 = i1 + 1
                i3 = i0 + 1

                edges = [
                    srf.InterpolatedCurveOnSurface([points[eval('i' + str(n))] for n in t], tolerance) for t in combinations
                ]

                subSrf, err = NurbsSurface.CreateNetworkSurface(
                    edges,
                    3,
                    0.1,
                    0.1,
                    1.0
                )
                id = doc.Objects.AddSurface(subSrf)

                countV += 1
            countU += 1

        return

    # BuildSubSurfaces()


subSurfaces = {}


def QuadGrid(patch, srf, u, v):
    '''
    Weaverbird | Creates a quad corner point grid on a surface.
    Parameters:
        srf : Rhino.Geometry.NurbsSurface
        u : int
            range(0,10)
        v : int
            range(0,10)
    Returns:
        quad : tuple<Rhino.Geometry.Point3d>
        midPoint : Rhino.Geometry.Point3d
            The midpoint of the quad
        normals : Rhino.Geometry.Vector3d
            Normal vector at midpoint
    '''
    tolerance = doc.ModelAbsoluteTolerance
    quad = range(4)
    combinations = zip(quad, (1, 2, 3, 0))

    result, maxU, maxV = srf.GetSurfaceSize()
    srf.SetDomain(0, Interval(0, 1))
    srf.SetDomain(1, Interval(0, 1))

    brep = Brep.TryConvertBrep(srf)
    srf = brep.Faces[0]

    midPoints = Point3dList()
    normals = []

    p0 = Point3dList()
    p1 = Point3dList()
    p2 = Point3dList()
    p3 = Point3dList()

    _u = 1.0 / (float(u) / 5.0)
    _v = 1.0 / (float(v) / 5.0)

    # subSurfaces[patch.Phase] = {}
    # subSurfaces[patch.Phase][key] = {}

    for i in range(u):
        for j in range(v):
            midPoint = srf.PointAt((i * _u) + (0.5 * _u), (j * _v) + (0.5 * _v))
            vector = srf.NormalAt((i * _u) + (0.5 * _u), (j * _v) + (0.5 * _v))

            uv0 = (float(i * _u), float(j * _v))
            uv1 = (float(i + 1.0) * _u, float(j * _v))
            uv2 = (float(i + 1.0) * _u, float(j + 1.0) * _v)
            uv3 = (float(i * _u), float(j + 1.0) * _v)

            c0 = srf.PointAt(*uv0)
            c1 = srf.PointAt(*uv1)
            c2 = srf.PointAt(*uv2)
            c3 = srf.PointAt(*uv3)

            edges = [
                srf.InterpolatedCurveOnSurface([eval('c' + str(n)) for n in t], tolerance) for t in combinations
            ]

            # subSrf = Brep.CreateEdgeSurface(edges)
            # id = doc.Objects.AddBrep(subSrf)

            subSrf, err = NurbsSurface.CreateNetworkSurface(
                edges,
                1,
                0.1,
                0.1,
                1.0
            )
            id = doc.Objects.AddSurface(subSrf)

            k1, k2 = patch.Phase
            key = ';'.join([str(n) for n in (k1, k2, i, j)])
            # subSurfaces[patch.Phase][key][(i,j)] = subSrf
            subSurfaces[key] = subSrf

            midPoints.Add(midPoint)
            p0.Add(c0)
            p1.Add(c1)
            p2.Add(c2)
            p3.Add(c3)
            normals.append(vector)

    return midPoints, p0, p1, p2, p3, normals


# TODO
# Brep.Reverse()
# Brep.Transpose()
# Brep.Direction()
# rs.Command('MakeUniform')
# rs.Command('MakeUniformUV')
#
#
# Surface.Fit()
#
#
# Surface.GetUserStrings()
# Surface.IsoCurve()
# print(Surface.ShortPath())
# print(Surface.UserData())
#
# brep.CreateShell()


builder = scriptcontext.sticky['builder']
log = open('./log.txt', 'w')

patch = builder.Patches[0]
srf1 = patch.Surfaces[1]['S']['S_1']
# srf2 = patch.Surfaces[1]['S']['S_2']
# srf3 = patch.Surfaces[2]['S']['S0_0']


for patch in builder.Patches:
    for (key, srf) in patch.Surfaces[1]['S'].iteritems():
        if srf:
            # ExtractIsoCurves(srf)
            BuildIsoCurves(srf, 50, 50, trimAware=True, euqalizeSpanLength=True)

            # QuadGrid(patch, srf, srf.SpanCount(0), srf.SpanCount(1))  # srf.Points.CountU, srf.Points.CountV)

# log.write(str(subSurfaces))

# s = subSurfaces.values()[0]
# br = s.ToBrep()
#
# combinations = itertools.combinations(subSurfaces.keys(), 2)

def IntersectSurfaces():
    tolerance = 10  # doc.ModelAbsoluteTolerance

    Curves = CurveList()
    Points = Point3dList()

    breps = subSurfaces

    # Use "smallest" divisions to demarcate patch self-intersection(s)
    for (a, b) in combinations:
        a = a in breps and breps[a] # .ToBrep()
        b = b in breps and breps[b] # .ToBrep()

        edgesA = a.ToBrep().DuplicateNakedEdgeCurves(outer=True, inner=False)
        edgesB = b.ToBrep().DuplicateNakedEdgeCurves(outer=True, inner=False)

        EA = [(edge.PointAtStart, edge.PointAtEnd) for edge in edgesA]
        EB = [(edge.PointAtStart, edge.PointAtEnd) for edge in edgesB]

        # edges = a.Edges.GetEnumerator()  # Brep
        # EA = ((e.PointAtStart, e.PointAtEnd) for e in edges)
        # EB = ((e.PointAtStart, e.PointAtEnd) for e in b.Edges.GetEnumerator())

        if a and b:
            r, curves, ponints = Intersect.Intersection.SurfaceSurface(a, b, tolerance)

            # if r:
                # log.write('\n' + str(curves[0].PointAtStart))

            for curve in curves:
                C1 = curve.PointAtStart
                C2 = curve.PointAtEnd

                match = False
                for (E1, E2) in EA:
                    if C1.EpsilonEquals(E1, 0.1) or C2.EpsilonEquals(E2, 0.1) or C1.EpsilonEquals(E2, 0.1) or C2.EpsilonEquals(E1, 0.1):  # reverse
                        match = True
                        break

                for (E1, E2) in EB:
                    if C1.EpsilonEquals(E1, 0.1) or C2.EpsilonEquals(E2, 0.1) or C1.EpsilonEquals(E2, 0.1) or C2.EpsilonEquals(E1, 0.1):  # reverse
                        match = True
                        break

                if not match:
                    Curves.Add(curve)

    # for point in Points:
    #     # id = doc.Objects.AddPoint(point)
    #     # self.__rendered__(id)
    #     # rs.ObjectLayer(id, 'Intersect::Points')
    #     pass

    # print Curves.Count
    for curve in Curves:
        doc.Objects.AddCurve(curve)

    return Curves, Points


# srf = builder.Surfaces[1][0]
# polysrf = builder.PolySurface[1]
# brep = Brep.TryConvertBrep(srf)

#
# # http://www.grasshopper3d.com/profiles/blogs/reverse-and-swap-u-and-v-directions-of-surface
# def Dir(srf, reverse=None, swap=None):
#     '''
#     Equivalent to Rhino's `Dir` command
#
#     Grasshopper Lunchbox example:
#     ```
#         def ReverseSrfDirection(srf, direction=0):
#             if direction == 1:
#                 srf.Reverse(0)
#             elif direction == 2:
#                 srf.Reverse(1)
#             elif direction == 3:  # 'UV'
#                 srf.Transpose()
#
#             return srf
#     ```
#     '''
#     if reverse in (0, 2):  # Reverse U
#         minU, maxU = srf.Domain(0)
#         interval0 = Interval(-maxU, -minU)
#         srf.SetDomain(0, interval0)
#         srf = srf.Reverse(0)
#     elif reverse in (1, 2):  # Reverse V
#         minV, maxV = srf.Domain(1)
#         interval1 = Interval(-maxV, -minV)
#         srf.SetDomain(1, interval1)
#         srf = srf.Reverse(1)
#
#     if swap:  # Swap UV
#         srf = srf.Transpose()
#
#     anchor = srf.PointAt(0.0, 0.0)
#     maxU = srf.PointAt(0.5, 0.0)
#     maxV = srf.PointAt(0.0, 0.5)
#     uVector = maxU - anchor
#     vVector = maxV - anchor
#
#     return anchor, uVector, vVector, srf
#
#
# def PlotStartingPoints():
#     rs.AddLayer('Sorted', Color.Red)
#     rs.AddLayer('UnSorted', Color.Violet)
#
#     startingPoints = Point3dList()
#     for i, srf in enumerate(builder.Surfaces[1]):
#         startingPoints.Add(srf.Points.GetControlPoint(0, 0).Location)
#
#     sorted = rs.SortPoints(startingPoints)
#
#     id = rs.AddCurve(sorted, 1)
#     rs.ObjectLayer(id, 'Sorted')
#
#     id = rs.AddCurve(startingPoints, 1)
#     rs.ObjectLayer(id, 'UnSorted')
#
#
# def DivideOuterBordersAndExtractIsoCurveThroughDivision():
#     borders = Curve.JoinCurves(builder.Outer)
#
#     # points = curve.DivideEquidistant(10)
#     curve = borders[0]
#     divisions = curve.DivideByCount(10, True)
#     points = [curve.PointAt(t) for t in divisions]
#
#     done = []
#     DivU = Point3dList()
#
#     for i, srf in enumerate(builder.Surfaces[1]):
#         for point in points:
#             brep = Brep.TryConvertBrep(srf)
#             result, parameter = builder.ClosestPoint(brep, point, 0.1)
#
#             if result:
#                 done.append(srf)
#                 _u, _v = builder.ExtractIsoCurve(srf, parameter, 0)
#
#                 for curve in _u:
#                     doc.Objects.AddCurve(curve)
#                     rs.AddPoint(curve.PointAtEnd)
#                     DivU.Add(curve.PointAtEnd)
#
#
# def Normals():
#     for i, srf in enumerate(builder.Surfaces[1]):
#         direction = srf.NormalAt(0, 0)
#         rs.AddPoint(direction)
#
#         # if srf.OrientationIsReversed:
#         #     direction.Reverse()
#         #
#         # "Surface normal at uv(0,0) = ({0:f},{1:f},{2:f})"
#
#         # log.write(str(direction.X))
#
#
# def ExtractIsoCurvesFromBaseCurveDivisions(srf):
#     _ = builder.AnalyseSurface(srf)
#
#     if i == 0:
#         UDiv = Point3dList()
#         VDiv = Point3dList()
#
#         # base = Point3dList()
#         # for u in range(srf.Points.CountU):
#         #     base.Add(srf.Points.GetControlPoint(u, 0).Location)
#         # Then create the curve from base points list
#
#         _u, _v = builder.ExtractIsoCurve(srf, (0, 0), 1)
#         baseCurve = _v[0]
#
#         # UDiv = baseCurve.DivideByLength(2.5, True)  # Curve Parameters
#         # points = [baseCurve.PointAt(t) for t in UDiv]
#         # for parameter in divisions:
#         #     _u, _v = builder.ExtractIsoCurve(srf, (None, parameter), 0)
#         #     for curve in _u:
#         #         doc.Objects.AddCurve(curve)
#         #         UDiv.Add(curve.PointAtEnd)
#
#         points = baseCurve.DivideEquidistant(10)
#
#         for point in points:
#             brep = Brep.TryConvertBrep(srf)
#             result, parameter = builder.ClosestPoint(brep, point, 0.1)
#             _u, _v = builder.ExtractIsoCurve(srf, parameter, 0)
#
#             for curve in _u:
#                 doc.Objects.AddCurve(curve)
#                 UDiv.Add(curve.PointAtEnd)
#
#     if i == 1:
#         for point in UDiv:
#             brep = Brep.TryConvertBrep(srf)
#             result, parameter = builder.ClosestPoint(brep, point, 0.1)
#             u, v = parameter
#             _u, _v = builder.ExtractIsoCurve(srf, (u, v), 0)
#             for curve in _u:
#                 doc.Objects.AddCurve(curve)
#
#
# def ExtractIsoCurvesForPair(srf, n):
#     _ = builder.AnalyseSurface(srf)
#     UDiv = None
#     VDiv = None
#
#     if n == 0:
#         UDiv = Point3dList()
#         VDiv = Point3dList()
#
#         for u in rs.frange(_['minU'], _['maxU'], _['stepU']):
#             _u, _v = builder.ExtractIsoCurve(srf, (u, None), 1)
#
#             for curve in _v:
#                 # rs.AddPoint(curve.PointAtEnd)
#                 VDiv.Add(curve.PointAtEnd)
#                 doc.Objects.AddCurve(curve)
#
#         for v in rs.frange(_['minV'], _['maxV'], _['stepV']):
#             _u, _v = builder.ExtractIsoCurve(srf, (None, v), 1)
#
#             for curve in _u:
#                 # rs.AddPoint(curve.PointAtEnd)
#                 UDiv.Add(curve.PointAtEnd)
#                 doc.Objects.AddCurve(curve)
#
#     if n == 1:
#         for point in UDiv:
#             brep = Brep.TryConvertBrep(srf)
#             result, parameter = builder.ClosestPoint(brep, point, 0.1)
#             _u, _v = builder.ExtractIsoCurve(srf, parameter, 1)
#
#             for curve in _v:
#                 doc.Objects.AddCurve(curve)
#
#         for point in VDiv:
#             brep = Brep.TryConvertBrep(srf)
#             result, parameter = builder.ClosestPoint(brep, point, 0.1)
#             _u, _v = builder.ExtractIsoCurve(srf, parameter, 0)
#
#             for curve in _u:
#                 doc.Objects.AddCurve(curve)
#
#
# def ExtractIsoCurvesByDividingSurfaceDomain(srf):
#     # NURBS geometry parameter space divisions are not equivalent to length.
#     # https://ieatbugsforbreakfast.wordpress.com/2013/09/27/curve-parameter-space/
#     _ = builder.AnalyseSurface(srf)
#     U = CurveList()
#     V = CurveList()
#
#     for parameter in rs.frange(_['minV'], _['maxV'], _['stepV']):
#         _u, _v = builder.ExtractIsoCurve(srf, (parameter, None), 1)
#         for curve in _v:
#             V.Add(curve)
#
#     # for parameter in rs.frange(_['minU'], _['maxU'], _['stepU']):
#     #     _u, _v = builder.ExtractIsoCurve(srf, (parameter, None), 1)
#     #     for curve in _v:
#     #         V.Add(curve)
#
#     return U, V
#
#
# def ExtractIsoCurvesAtSrfControlPoints(srf):
#     U = CurveList()
#     V = CurveList()
#
#     for u in range(0, srf.Points.CountU, 2):
#         p = srf.Points.GetControlPoint(u, 0).Location
#         result, _u, _v = srf.ClosestPoint(p)
#         _u, _v = builder.ExtractIsoCurve(srf, (_u, _v), 1)
#
#         for curve in _v:
#             V.Add(curve)
#
#     for v in range(0, srf.Points.CountV, 2):
#         p = srf.Points.GetControlPoint(0, v).Location
#         result, _u, _v = srf.ClosestPoint(p)
#         _u, _v = builder.ExtractIsoCurve(srf, (_u, _v), 0)
#
#         for curve in _u:
#             U.Add(curve)
#
#     return U, V
#
#
# def SampleSurfacePoints(srf):
#     arr = []
#     U = srf.Points.CountU - 1
#     V = srf.Points.CountV - 1
#
#     for u in (0, U / 2, U):
#         for v in (0, V / 2, V):
#             arr.append((u, v))
#
#     return arr
#
#
# def OrientSurfacesToReference(builder):
#     def compare(a, b, coordinate):
#         '''
#         Parameters:
#             a : Rhino.Geometry.Vector3d
#             b : Rhino.Geometry.Vector3d
#             coordinate : str
#         '''
#         a = getattr(a, coordinate)
#         b = getattr(b, coordinate)
#
#         if (a > 0 and b > 0) or (a < 0 and b < 0):
#             print coordinate + ' match'
#             return True
#         else:
#             print 'flip ' + coordinate
#             return False
#
#         '''
#         Returns:
#             -1 if a < b
#             0 if a == b
#             1 if b > b
#
#         return a.CompareTo(b)
#         '''
#
#     ref = builder.BuildReferenceSphere((0, 0, 0), builder.Analysis['radius'])
#     refBrep = ref.ToBrep()
#     id = doc.Objects.AddSphere(ref)
#
#     results = []
#
#     for srf in builder.Surfaces[1]:  # srf = builder.Surfaces[1][0]
#         for (u, v) in SampleSurfacePoints(srf):
#             # srfTargetPlane = srf.FrameAt(u, v)[1]
#             srfPoint = srf.Points.GetControlPoint(u, v).Location
#             srfNormal = srf.NormalAt(u, v)
#
#             projection = refBrep.ClosestPoint(srfPoint, radius)
#             refPoint = projection[1]
#             refParameter = projection[3:4]
#             refNormal = projection[5]
#
#             srf.Translate(refNormal)
#
#             # doc.Objects.AddLine(srfPoint, refPoint)
#
#             if compare(refNormal, srfNormal, 'X'):
#                 pass
#
#             if compare(refNormal, srfNormal, 'Y'):
#                 pass
#
#             if compare(refNormal, srfNormal, 'Z'):
#                 pass
#
#                 id = builder.Rendered['Surfaces'][1][0]
#                 rs.FlipSurface(id, True)
#
#             # for i, axis in enumerate(('X', 'Y')):  # 'Z'
#             #     if not compare(refNormal, srfNormal, axis):
#             #         # srf.Reverse(i)
#             #         srf.Transpose()
#
#     return results
#
#
# # OrientSurfacesToReference(builder)
#
#
# # for p, patch in enumerate(builder.Patches):
# #     for e in ('U'):  # , 'V'
# #         for c1, curve in enumerate(patch.IsoCurves[e]):
# #             closest = None
# #             point = curve.PointAtEnd
# #
# #             for c2, other in enumerate(builder.IsoCurves[e]):
# #                 result, t = other.ClosestPoint(point, 0.1)
# #                 if result:
# #                     testPoint = other.PointAt(t)
# #                     distance = point.DistanceTo(testPoint)
# #                     if closest is None or distance < closest[0]:
# #                         closest = distance, c2, testPoint
# #
# #             distance, c2, testPoint = closest
# #             start.append((p, c1, c2))
# #
# #             # log.write("\n" + str(curve.TangentAtEnd))
# #             # curve.TangentAtStart
# #             # curve.TangentAt(1)
#
#
# def OrderIsoCurvesByProximity():
#     ordered = []
#     tolerance = 0.1  # doc.ModelAbsoluteTolerance
#     colours = (Color.Teal, Color.Red)
#     for e in ('U'):  # , 'V'
#         for c1, curve in enumerate(builder.IsoCurves[e]): # .GetRange(0, 10)
#             closest = None
#             point = curve.PointAtEnd
#
#             for c2, other in enumerate(builder.IsoCurves[e]):
#                 if curve != other:
#                     start = other.PointAtStart
#                     end = other.PointAtEnd
#
#                     if Point3d.EpsilonEquals(point, start, 0.1) or \
#                        Point3d.EpsilonEquals(point, end, 0.1):
#                         ordered.append((c1, c2))
#                         break
#
#                 # result, t = other.ClosestPoint(point, tolerance)
#                 # if result:
#                 #     testPoint = other.PointAt(t)
#                 #     distance = point.DistanceTo(testPoint)
#                 #     if closest is None or distance < closest[0]:
#                 #         closest = distance, c2, testPoint
#
#             # distance, c2, testPoint = closest
#             # ordered.append((c1, c2))
#
#         for combination in ordered:
#             for i, pos in enumerate(combination):
#                 layer = rs.AddLayer('::'.join(('Combinations', str(i))), colours[i])
#                 curve = builder.IsoCurves[e][pos]
#                 id = doc.Objects.AddCurve(curve)
#                 rs.ObjectLayer(id, layer)
#
#
# def OrderPatchesByCurveContinuity():
#     # start at k1, k2
#     #     take the first curve within the patch
#     #     iterate through all curves to the find the next by closest point
#     #     add patch index to order list
#     #         take this new found patch and repeat until we have gone through all patches
#
#     tolerance = 0.1  # doc.ModelAbsoluteTolerance
#
#     ref = builder.BuildReferenceSphere((0, 0, 0), builder.Analysis['radius'])
#     refBrep = ref.ToBrep()
#
#     patchOrder = []
#     curveOrder = []
#     disoriented = []
#
#     def FindPatchMaxCurve(curves):
#         closest = None
#
#         # Find the outer most curve by proximity to reference sphere
#         for curve in (curves.First, curves.Last):
#             point = curve.PointAtEnd
#             projection = refBrep.ClosestPoint(point, radius * 2.0)
#             distance = point.DistanceTo(projection[1])
#
#             if closest is None or distance < closest[0]:
#                 closest = distance, curve, point
#
#         return closest
#
#     exampleCurves = {}
#
#     # Direction seems to alternate so iterate every second patch targeting those patches
#     # needing to be flipped.
#     #
#     # for p1, patch1 in enumerate(builder.Patches[::2]):
#     for p1, patch1 in enumerate(builder.Patches):
#         # Use U because of continuity around the entire surface
#         curves = patch1.IsoCurves['Uniform']['U']
#         count = len(curves)
#         # track position within global builder.IsoCurves['Uniform']['U'] collection
#         globalPos = (p1 + 1) * count
#
#         connection = None
#         distanceFromRefSphere, patchMax, point = FindPatchMaxCurve(curves)
#
#         for p2, patch2 in enumerate(builder.Patches):
#             if patch1 != patch2:
#                 curves2 = patch2.IsoCurves['Uniform']['U']
#                 count2 = len(curves2)
#                 globalPos2 = (p2 + 1) * count
#
#                 # We may need to use both first and last curves here.
#                 # When n i odd some of the patches may straddle the centre making it difficult to
#                 # determine the outermost edge.
#                 # curve = FindPatchMaxCurve(curves2)[1]
#                 for i, curve in enumerate((curves2.First, curves2.Last)):
#                     if not connection:
#                         # We need to test connection at both ends because patch direction
#                         # alternates.
#                         start = curve.PointAtStart
#                         end = curve.PointAtEnd
#                         pos2 = globalPos2 + 0
#
#                         # directions match if start to end connection
#                         continuous = Point3d.EpsilonEquals(point, start, tolerance)
#                         # directions NOT matched if end to end connection
#                         discontinuous = Point3d.EpsilonEquals(point, end, tolerance)
#
#                         if discontinuous:
#                             # disoriented.append(p2)
#                             # And reverse all curves before we find patch2's neighbour
#                             for curve in patch2.IsoCurves['Uniform']['U']:
#                                 curve.Reverse()
#
#                         if continuous or discontinuous:
#                             connection = p2, curve
#                             patchOrder.append((p1, p2))
#
#                             if i == 1:
#                                 exampleCurves[p2] = curves2.First
#                             else:
#                                 exampleCurves[p2] = curve
#
#                             break
#
#     print(patchOrder)
#
#     patches = len(builder.Patches)
#     loops = []
#
#     loop = [0]
#     count = 0
#
#     for i in range(patches):
#         p1, p2 = next(x for x in patchOrder if x[0] == loop[-1])
#         if count > 0 and p2 == 0:
#             break
#         loop.append(p2)
#         count += 1
#     loops.append(loop)
#
#     # breaks = []
#     # p1s = [p1 for (p1, p2) in patchOrder]
#     # for e in p1s:
#     #     if e not in loop:
#     #         breaks.append(e)
#     #
#     # for n in breaks:
#     #     loop = [n]
#     #     count = 0
#     #     for i in range(patches):
#     #         p1, p2 = next(x for x in patchOrder if x[0] == loop[-1])
#     #         if count > 0 and p2 == 0:
#     #             break
#     #         loop.append(p2)
#     #         count += 1
#     #     loops.append(loop)
#
#     print loops
#
#     for i, p in enumerate(loops[0]):
#         try:
#             curve = exampleCurves[p]
#             centre = curve.PointAtNormalizedLength(0.5)
#             rs.AddTextDot(i, centre)
#         except:
#             pass
#
#
#     # for i, (p1, p2) in enumerate(patchOrder):
#     #     patchIndex, curve = p2
#     #     centre = curve.PointAtNormalizedLength(0.5)
#     #     rs.AddTextDot(i, centre)
#     #
#     #     for srf in builder.Patches[patchIndex].Surfaces[1]:
#     #         srf.Transpose()
#     #
#     #     for brep in builder.Patches[patchIndex].Breps[1]:
#     #         brep.Flip()
#     #         # print brep.Faces[0].OrientationIsReversed
#
#     return patchOrder
#
#
# # OrderPatchesByCurveContinuity()
#
#
# def OrderPatchesByPointOccurence():
#     pointCount = builder.n * (builder.n * (builder.U * builder.V))  # len(builder.Points)
#     patchPointCount = pointCount / builder.n
#     # builder.Analysis['U/2'] * builder.V
#     srfPointCount = (patchPointCount / builder.n) / 2
#
#
# def InterpCrvThroguhControlPoints(srf, grid):
#     pass
#     # V = []
#     # U = []
#     #
#     # U2 = []
#     # V2 = []
#     #
#     # U3 = []
#     # V3 = []
#     #
#     # MinDomainU, MaxDomainU = srf.Domain(0)
#     # MinDomainV, MaxDomainV = srf.Domain(1)
#     #
#     # for u in range(srf.Points.CountU):
#     #     u3 = float((float(u) + 1.0) / float(srf.Points.CountU)) * MaxDomainU
#     #     arr = Point3dList()
#     #     arr2 = []
#     #     arr3 = []
#     #
#     #     for v in range(srf.Points.CountV):
#     #         v3 = float((float(v) + 1.0) / float(srf.Points.CountV)) * MaxDomainV
#     #         arr.Add(srf.Points.GetControlPoint(u, v).Location)
#     #         arr2.append((u, v))
#     #         # arr3.append(Point2d(u3, v3))
#     #         arr3.append((u3, v3))
#     #
#     #     V.append(arr)
#     #     V2.append(arr2)
#     #     V3.append(arr3)
#     #
#     # for v in range(srf.Points.CountV):
#     #     v3 = float((float(v) + 1.0) / float(srf.Points.CountV)) * MaxDomainV
#     #     arr = Point3dList()
#     #     arr2 = []
#     #     arr3 = []
#     #
#     #     for u in range(srf.Points.CountU):
#     #         u3 = float((float(u) + 1.0) / float(srf.Points.CountU)) * MaxDomainU
#     #         arr.Add(srf.Points.GetControlPoint(u, v).Location)
#     #         arr2.append((u, v))
#     #         # arr3.append(Point2d(x=u3, y=v3))
#     #         arr3.append((u3, v3))
#     #
#     #     U.append(arr)
#     #     U2.append(arr2)
#     #     U3.append(arr3)
#     #
#     # log.write("\n" + str(U3))
#     # points = V[7]
#     # for point in points:
#     #     doc.Objects.AddPoint(point)
#
#     # srf = builder.Rendered['Surfaces'][1][0]
#     # rs.AddInterpCrvOnSrfUV()
#     # rs.AddInterpCrvOnSrf(srf, V[2])
#     # Surface.InterpolatedCurveOnSurface()
#     # for points in U:
#     # curve = srf.InterpolatedCurveOnSurface(V[2], 1)
#     # doc.Objects.AddCurve(curve)
#
#
#
#
#     # BrepFace.InterpolatedCurveOnSurface()
#     # brep = Brep.TryConvertBrep(srf)
#     # brepFace = brep.Faces[0]
#
#     # pp = Point3dList()
#     # for u in range(srf.Points.CountU):
#     #     pp.Add(srf.Points.GetControlPoint(u, 10).Location)
#
#     # a = builder.Patches[0].Points[0]
#     # b = builder.Patches[0].Points[30]
#     #
#     # a = builder.Patches[0].Points[300]
#     # b = builder.Patches[0].Points[320]
#     #
#     # a = srf.Points.GetControlPoint(0, 0).Location
#     # b = srf.Points.GetControlPoint(0, 28).Location
#
#
#
#     # a = grid['V'][0].First
#     # b = grid['V'][0].Last
#     #
#     # rs.AddTextDot('a', a)
#     # rs.AddTextDot('b', b)
#     # curve = srf.InterpolatedCurveOnSurface(V[2], 0.1)
#     # print curve
#     # doc.Objects.AddCurve(curve)
#
#     # for row in V:
#     #     curve = srf.InterpolatedCurveOnSurface(row, 0.1)
#     #     doc.Objects.AddCurve(curve)
#
#     # curve = brepFace.InterpolatedCurveOnSurface((a, b), 0.000001)
#     # print(curve)
#     # doc.Objects.AddCurve(curve)
#
#
# def SeperateUVFromExtractWireframe(srf):
#     # Run `ExtractWireframe`
#     # Iterate the curves
#     #   Run Dir() to find separate U from V curves
#     # Then Add/Remove as required
#     pass
#
#     # Generate a denser wireframe and select sub samples from it.
#     for i in range(1, 5, 1):
#         ids = builder.Rendered['PolySurface'][1]
#         layer = rs.AddLayer('::'.join(('Wireframe', str(i))))
#
#         U = CurveList()
#         V = CurveList()
#
#         for id in ids:
#             obj = rs.coercerhinoobject(id, True, True)
#             obj.Attributes.WireDensity = i
#             obj.CommitChanges()
#
#         rs.SelectObjects(ids)
#         rs.Command(
#             '_MakeUniform '
#             + '_ExtractWireframe '
#             + 'OutputLayer=Input '
#             + 'GroupOutput=Yes '
#             + '_Enter '
#         )
#
#
#         curves = CurveList()
#         for id in rs.LastCreatedObjects(True):
#             curve = rs.coercecurve(id)
#
#             # TODO Separate by direction
#             # for e in ('U', 'V'):
#             #     for curve in builder.IsoCurves[e]:
#             #         curve.TangentAtEnd
#             #         curve.TangentAtStart
#             #         curve.TangentAt(1)
#
#             direction = curve.NormalAt(0, 0)
#             N = False
#             E = False
#             S = False
#             W = False
#
#             if direction.X > 0:
#                 U.Add(curve)
#                 V.Add(curve)
#
#             if direction.Y > 0:
#                 U.Add(curve)
#                 V.Add(curve)
#
#             if direction.Z > 0:
#                 U.Add(curve)
#                 V.Add(curve)
#
#         for e in ('U', 'V'):
#             curves = eval(e)
#             layer = rs.AddLayer('::'.join(('Wireframe', str(i), e)))
#
#             for curve in Curve.JoinCurves(curves, 0.1, False):
#                 rs.ObjectLayer(id, layer)
#
#
# def RenderCurves(curves):
#     for curve in curves:
#         doc.Objects.AddCurve(curve)
#
#
# for n in range(2):
#     pass
#     # REPORT :
#     #   * Matches Wireframe
#     #   * Need to unify surface directions in order to decrease/increase wire count
#     #   * Whilst `MakeUniform` improves wireframe apperance it doesn't seem to affect control points
#     # U, V = ExtractIsoCurvesAtSrfControlPoints(srf)
#     # RenderCurves(U)
#     # RenderCurves(V)
#
#     # REPORT :
#     #   * Yeah don't divide surface domain as if it were length
#     # U, V = ExtractIsoCurvesByDividingSurfaceDomain(srf)
#     # RenderCurves(U)
#     # RenderCurves(V)
#
#
# # for n in range(4):
# for patch in builder.Patches:
#     # patch = builder.Patches[n]
#     # for n2 in range(2):
#     for i, srf in enumerate(patch.Surfaces[1]):
#         pass
#
#
# # REPORT :
# #   *
# # SeperateUVFromExtractWireframe()
#
# # for patch in builder.Patches:
# #     srf = patch.Surfaces[1][0]
# #     grid = patch.PointGrid[1][0]
#
# patch = builder.Patches[0]  # for patch in builder.Patches:
#
# for n, srf in enumerate(patch.Surfaces[1]):
#     pass
#     # REPORT :
#     #   *
#     # ExtractIsoCurvesForPair(srf, n)
#
#     # REPORT :
#     #   *
#     # ExtractIsoCurvesFromBaseCurveDivisions(srf)
#
#
# def Make2d():
#     '''
#     THIS WORKS!!!
#     Only problem is I don't know how to ammend the layers.
#
#
#
#     ROTTING OOZE
#     Especially in 2Dimension CY the seam bulges in all sorts of ugly ways. Curves interpolated over it are ripe. `MergeSrf`seems to improve the situation.
#     Maybe we could run a MergeSrf on all SurfaceCombinations. Bear in mind it will fuck the junction up.
#
#     TODO
#     - Fix intersections, we don't want the overlaps
#     - Are Brep Curve and Surface combinations actually correct, do we need to use object ids instesad.
#     - Finish Make2d
#     '''
#     # TODO staged Make2d
#     # Run make2d numerous times selecting only a small number of curves at a time. This seems to yield better output than throwing everythin at it at once. Silhouette edges are especially bad.
#     # Low < 0.1 tolerance works best.
#     builder = scriptcontext.sticky['builder']
#
#     rs.SelectObjects(
#         # *self.Rendered['IsoCurves']['U'], # Do a subset of either U or V at a time
#         builder.Rendered['Surfaces'][1] #  or *self.Rendered['PolySurface'][1]
#     )
#
#     RunScript(
#         '-Make2D DrawingLayout=CurrentView '
#         + 'ShowTangentEdges=No '
#         + 'CreateHiddenLines=No '
#         + 'MaintainSourceLayers=Yes '
#         + 'Enter '
#         + '-Invert ',
#         # + 'Hide '
#         # + 'SetView World Top ZE SelNone'
#         True
#     )
#
#     # TODO
#     #   Major improvement
#     #   We may want to step through each problem curve with the user getting confirmation before performing the trim.
#     # Find all curves with a gap larger than tolerance
#     # Say if a curve ends in the middle of nowhere
#     # does the meet another. it should so if it doesn't
#     #   then find the nearest curve and trim from end to intersection
#
#     # We should then join the curves, with a reasonable tolerance. Not too high or too low.
#
# # Make2d()
#
#
# def FlipCurve(target, guide):
#     '''
#     TODO
#         see examples/grasshopper/curve/flip.cs
#     '''
#     pass
#
#
# '''
# TODO
#     WHY DO't we use quarter dome to measure closest point that should give us a better indication of position
# '''
#
# def FlipSurface(target, guide):
#     '''
#     see examples/grasshopper/surface/flip.cs
#
#     Flip the normals of a surface based on local or remote geometry
#
#     Parameters:
#         target : Rhino.Geometry.BrepFace
#         guide : Rhino.Geometry.BrepFace
#     '''
#     pass
#     # import Grasshopper.Kernel
#     # import Grasshopper.Kernel.Types
#     # import Rhino.Geometry
#     # import SurfaceComponents.My.Resources
#     # import System
#     # import System.Drawing
#     #
#     # pass
#     #
#     # flag = False
#     # num = 0.0
#     # num1 = 0.0
#     # DomainU = target.Domain(0)
#     # DomainV = target.Domain(1)
#     # StepU = DomainU[1] / 3 * target.SpanCount(0)
#     # StepV = DomainV[1] / 3 * target.SpanCount(1)
#     # num4 = double.MaxValue
#     # num5 = double.NaN
#     # num6 = double.NaN
#     # num7 = double.NaN
#     # num8 = double.NaN
#     # MinU = DomainU[0]
#     # MaxU = DomainU[1]
#     # CountU = 0
#     #
#     # if ((StepU >= 0 ? MinU > MaxU : MinU < MaxU)):
#     #     break
#     # else:
#     #     MinV = DomainV[0]
#     #     MaxV = DomainV[1]
#     #     flag2 = StepV >= 0
#     #     CountV = MinV
#     #
#     # if ((flag2 ? MinV > MaxV : MinV < MaxV)):
#     #     break
#     # else:
#     #     point3d = target.PointAt(min, MinV)
#     #
#     #     if guide.ClosestPoint(point3d, num, num1):
#     #         num13 = point3d.DistanceTo(guide.PointAt(num, num1))
#     #         if (num13 < num4):
#     #             num4 = num13
#     #             num5 = min
#     #             num6 = MinV
#     #             num7 = num
#     #             num8 = num1
#     #
#     # CountV += StepV
#     # CountU += StepU
#     #
#     # if num7:
#     #     Vector3d vector3d = target.NormalAt(CountU, num6)
#     #     Vector3d vector3d1 = guide.NormalAt(num7, num8)
#     #     flag = vector3d.IsParallelTo(vector3d1, 1.5707963267949) == -1
#     # else:
#     #     flag = False
#     # return flag
#
#
# def ExtendPrimitiveRhinoClasses():
#     '''
#     https://wiki.python.org/moin/HowTo/Sorting#Odd_and_Ends
#
#     The below code demonstrates how to extend an exisiting class defintion attributes dynamically. This approach works from the console, though not in Rhino -- `dictproxy` does not allow assignment
#     '''
#     def __eq__(self, other):
#         return self.PointAtStart == other.PointAtStart and \
#         self.PointAtEnd == other.PointAtEnd
#
#     def __ne__(self, other):
#         return not self.__eq__(other)
#
#     def __lt__(self, other):
#         return
#
#     def __le__(self, other):
#         return
#
#     def __gt__(self, other):
#         return
#
#     def __ge__(self, other):
#         return
#
#     Curve.__dict__['__eq__'] = __eq__
#     Curve.__dict__['__ne__'] = __ne__
#     Curve.__dict__['__lt__'] = __lt__
#     Curve.__dict__['__le__'] = __le__
#     Curve.__dict__['__gt__'] = __gt__
#     Curve.__dict__['__ge__'] = __ge__
