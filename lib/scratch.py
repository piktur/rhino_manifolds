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
import Rhino.Geometry.Mesh as Mesh
import Rhino.Geometry.BrepFace as BrepFace
import Rhino.Geometry.Brep as Brep
import Rhino.Geometry.Intersect as Intersect
import Rhino.Geometry.Curve as Curve
import Rhino.Geometry.Interval as Interval
import Rhino.Geometry.Sphere as Sphere
import Rhino.Geometry.Transform as Transform
from Rhino.Collections import Point3dList, CurveList
import Rhino.Geometry as Geometry
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
#
# brep.CreateShell()
# brep.SolidOrientation()
# brep.Loops()
# brep.Curves2D()

builder = scriptcontext.sticky['builder']
log = open('./log.txt', 'w')

# srf = builder.Surfaces['Div1'][0]
# polysrf = builder.PolySurface['Div1']
# brep = Brep.TryConvertBrep(srf)


# http://www.grasshopper3d.com/profiles/blogs/reverse-and-swap-u-and-v-directions-of-surface
def Dir(srf, reverse=None, swap=None):
    '''
    Equivalent to Rhino's `Dir` command

    Grasshopper Lunchbox example:
    ```
        def ReverseSrfDirection(srf, direction=0):
            if direction == 1:
                srf.Reverse(0)
            elif direction == 2:
                srf.Reverse(1)
            elif direction == 3:  # 'UV'
                srf.Transpose()

            return srf
    ```
    '''
    if reverse in (0, 2):  # Reverse U
        minU, maxU = srf.Domain(0)
        interval0 = Interval(-maxU, -minU)
        srf.SetDomain(0, interval0)
        srf = srf.Reverse(0)
    elif reverse in (1, 2):  # Reverse V
        minV, maxV = srf.Domain(1)
        interval1 = Interval(-maxV, -minV)
        srf.SetDomain(1, interval1)
        srf = srf.Reverse(1)

    if swap:  # Swap UV
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
    _['U'] = srf.SpanCount(0)  # srf.Points.CountU
    _['V'] = srf.SpanCount(1)  # srf.Points.CountV
    # _[''] = srf.OrderU
    # _[''] = srf.OrderV
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


def BuildReferenceSphere(centre=(0, 0, 0), radius=200):
    center = rs.coerce3dpoint(centre)
    return Sphere(center, radius)


def Dimensions():
    box = builder.BoundingBox
    origin = box[0]

    dim = [(origin - box[i]).Length for i in (1, 3, 4)]
    x, y, z = dim
    # dim.sort()

    diag = [(box[a] - box[b]).Length for (a, b) in itertools.combinations((1, 3, 4), 2)]
    xy, xz, yz = diag
    # diag.sort()

    diameter = max(diag)
    radius = diameter / 2.0

    return diameter, radius, dim, diag


def BoxAnalysis():
    box = Brep.CreateFromBox(builder.BoundingBox)

    print Geometry.AreaMassProperties.Compute(box)
    print Geometry.VolumeMassProperties.Compute(box)


def SampleSurfacePoints(srf):
    arr = []
    U = srf.Points.CountU - 1
    V = srf.Points.CountV - 1

    for u in (0, U / 2, U):
        for v in (0, V / 2, V):
            arr.append((u, v))

    return arr


def OrientSurfacesToReference(builder):
    def compare(a, b, coordinate):
        '''
        Parameters:
            a : Rhino.Geometry.Vector3d
            b : Rhino.Geometry.Vector3d
            coordinate : str
        '''
        a = getattr(a, coordinate)
        b = getattr(b, coordinate)

        if (a > 0 and b > 0) or (a < 0 and b < 0):
            print coordinate + ' match'
            return True
        else:
            print 'flip ' + coordinate
            return False

        '''
        Returns:
            -1 if a < b
            0 if a == b
            1 if b > b

        return a.CompareTo(b)
        '''

    diameter, radius, dim, diag = Dimensions()

    ref = BuildReferenceSphere((0, 0, 0), radius)
    refBrep = ref.ToBrep()
    id = doc.Objects.AddSphere(ref)

    results = []

    for srf in builder.Surfaces['Div1']:  # srf = builder.Surfaces['Div1'][0]
        for (u, v) in SampleSurfacePoints(srf):
            # srfTargetPlane = srf.FrameAt(u, v)[1]
            srfPoint = srf.Points.GetControlPoint(u, v).Location
            srfNormal = srf.NormalAt(u, v)

            projection = refBrep.ClosestPoint(srfPoint, radius)
            refPoint = projection[1]
            refParameter = projection[3:4]
            refNormal = projection[5]

            srf.Translate(refNormal)

            # doc.Objects.AddLine(srfPoint, refPoint)

            if compare(refNormal, srfNormal, 'X'):
                pass

            if compare(refNormal, srfNormal, 'Y'):
                pass

            if compare(refNormal, srfNormal, 'Z'):
                pass

                id = builder.Rendered['Surfaces']['Div1'][0]
                rs.FlipSurface(id, True)

            # for i, axis in enumerate(('X', 'Y')):  # 'Z'
            #     if not compare(refNormal, srfNormal, axis):
            #         # srf.Reverse(i)
            #         srf.Transpose()

    return results


# OrientSurfacesToReference(builder)


# for p, patch in enumerate(builder.Patches):
#     for e in ('U'):  # , 'V'
#         for c1, curve in enumerate(patch.IsoCurves[e]):
#             closest = None
#             point = curve.PointAtEnd
#
#             for c2, other in enumerate(builder.IsoCurves[e]):
#                 result, t = other.ClosestPoint(point, 0.1)
#                 if result:
#                     testPoint = other.PointAt(t)
#                     distance = point.DistanceTo(testPoint)
#                     if closest is None or distance < closest[0]:
#                         closest = distance, c2, testPoint
#
#             distance, c2, testPoint = closest
#             start.append((p, c1, c2))
#
#             # log.write("\n" + str(curve.TangentAtEnd))
#             # curve.TangentAtStart
#             # curve.TangentAt(1)


def OrderIsoCurvesByProximity():
    ordered = []
    tolerance = 0.1  # doc.ModelAbsoluteTolerance
    colours = (Color.Teal, Color.Red)
    for e in ('U'):  # , 'V'
        for c1, curve in enumerate(builder.IsoCurves[e]): # .GetRange(0, 10)
            closest = None
            point = curve.PointAtEnd

            for c2, other in enumerate(builder.IsoCurves[e]):
                if curve != other:
                    start = other.PointAtStart
                    end = other.PointAtEnd

                    if Point3d.EpsilonEquals(point, start, 0.1) or \
                       Point3d.EpsilonEquals(point, end, 0.1):
                        ordered.append((c1, c2))
                        break

                # result, t = other.ClosestPoint(point, tolerance)
                # if result:
                #     testPoint = other.PointAt(t)
                #     distance = point.DistanceTo(testPoint)
                #     if closest is None or distance < closest[0]:
                #         closest = distance, c2, testPoint

            # distance, c2, testPoint = closest
            # ordered.append((c1, c2))

        for combination in ordered:
            for i, pos in enumerate(combination):
                layer = rs.AddLayer('::'.join(('Combinations', str(i))), colours[i])
                curve = builder.IsoCurves[e][pos]
                id = doc.Objects.AddCurve(curve)
                rs.ObjectLayer(id, layer)


def OrderPatches():
    # start at k1, k2
    #     take the first curve within the patch
    #     iterate through all curves to the find the next by closest point
    #     add patch index to order list
    #         take this new found patch and repeat until we have gone through all patches

    tolerance = 0.1  # doc.ModelAbsoluteTolerance
    diameter, radius, dim, diag = Dimensions()

    ref = BuildReferenceSphere((0, 0, 0), radius)
    refBrep = ref.ToBrep()

    patchOrder = []
    curveOrder = []
    disoriented = []

    def FindPatchMaxCurve(curves):
        closest = None

        # Find the outer most curve by proximity to reference sphere
        for curve in (curves.First, curves.Last):
            point = curve.PointAtEnd
            projection = refBrep.ClosestPoint(point, radius * 2.0)
            distance = point.DistanceTo(projection[1])

            if closest is None or distance < closest[0]:
                closest = distance, curve, point

        return closest

    # Direction seems to alternate so iterate every second patch targeting those patches
    # needing to be flipped.
    #
    # for p1, patch1 in enumerate(builder.Patches[::2]):
    for p1, patch1 in enumerate(builder.Patches):
        # Use U because of continuity around the entire surface
        curves = patch1.IsoCurves['Uniform']['U']
        count = len(curves)
        # track position within global builder.IsoCurves['Uniform']['U'] collection
        globalPos = (p1 + 1) * count

        connection = None
        distanceFromRefSphere, patchMax, point = FindPatchMaxCurve(curves)

        for p2, patch2 in enumerate(builder.Patches):
            if patch1 != patch2:
                curves2 = patch2.IsoCurves['Uniform']['U']
                count2 = len(curves2)
                globalPos2 = (p2 + 1) * count

                # We may need to use both first and last curves here.
                # When n i odd some of the patches may straddle the centre making it difficult to
                # determine the outermost edge.
                # curve = FindPatchMaxCurve(curves2)[1]
                for curve in (curves2.First, curves2.Last):
                    if not connection:
                        # We need to test connection at both ends because patch direction
                        # alternates.
                        start = curve.PointAtStart
                        end = curve.PointAtEnd
                        pos2 = globalPos2 + 0

                        # directions match if start to end connection
                        continuous = Point3d.EpsilonEquals(point, start, tolerance)
                        # directions NOT matched if end to end connection
                        discontinuous = Point3d.EpsilonEquals(point, end, tolerance)

                        if discontinuous:
                            # disoriented.append(p2)
                            # And reverse all curves before we find patch2's neighbour
                            for curve in patch2.IsoCurves['Uniform']['U']:
                                curve.Reverse()

                        if continuous or discontinuous:
                            connection = p2, curve
                            patchOrder.append((p1, p2))

                            break

    print(patchOrder)

    order = [0]
    patches = len(builder.Patches)
    count = 0

    for i in range(count):
        p1, p2 = next(x for x in patchOrder if x[0] == order[-1])
        if count > 0 and p2 == 0:
            break
        else:
            order.append(p2)
            count += 1

    # rem = []
    # p1s = [p1 for (p1, p2) in patchOrder]
    # for e in p1s:
    #     if e not in order:
    #         rem.append(e)
    #
    # [(0, 3), (1, 7), (2, 0), (3, 4), (4, 7), (5, 8), (6, 3), (7, 8), (8, 2)]
    # [0, 3, 4, 7, 8, 2, 7, 8, 3]
    #
    # for e in rem:
    #     p1, p2 = next(x for x in patchOrder if x[0] == e)
    #     order.append(p2)

    # # for i in range(count):
    # while len(patchOrder) > 0:
    #     p1, p2 = patchOrder.pop()
    #     order.append(p2)
    #     order.append(cont
    #     for (p1, p2) in patchOrder:
    #         cont = (p1, p2)


    # for i, (p1, p2) in enumerate(patchOrder):
    #     if i == 0:
    #         order.append(p1)
    #     else:
    #         order.append(p2)
    #         # order.append(patchOrder[p1][1])

    print order

    # for i, (p1, p2) in enumerate(patchOrder):
    #     patchIndex, curve = p2
    #     centre = curve.PointAtNormalizedLength(0.5)
    #     rs.AddTextDot(i, centre)
    #
    #     for srf in builder.Patches[patchIndex].Surfaces['Div1']:
    #         srf.Transpose()
    #
    #     for brep in builder.Patches[patchIndex].Breps['Div1']:
    #         brep.Flip()
    #         # print brep.Faces[0].OrientationIsReversed

    return patchOrder


OrderPatches()


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
            # for e in ('U', 'V'):
            #     for curve in builder.IsoCurves[e]:
            #         curve.TangentAtEnd
            #         curve.TangentAtStart
            #         curve.TangentAt(1)

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
