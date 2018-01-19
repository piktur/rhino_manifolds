import cmath
import math
from math import cos, sin, pi
import System.Enum
from scriptcontext import doc
import rhinoscriptsyntax as rs
from Rhino.Geometry import Point3d, NurbsSurface, ControlPoint, NurbsCurve, Polyline
from Rhino.Geometry import Curve, Brep, Vector3d, CurveKnotStyle
from Rhino.Collections import Point3dList, CurveList

import json


# "k1, k2" PHASE
# ATTRACTOR POINTS AS DEMONSTRATED IN THIS [VIDEO](https://www.youtube.com/watch?v=Vyst-H_muuI) may produce better results than current approach. Exlpore this is Kurt unsatisfied with surf continuity.
#
# TOOD
# - Generate all possible variable combinations. Doing so will remove clback mechanism.
# Won't work, we still want to be able to do things before,around etc eh loop
# VARS = [[k1, k2, a, b], [k1, k2, a, b]]
# def Mesh():
#     for [k1, k2, a, b] in VARS:
#         # do
# - Explore "continuity"  http://docs.mcneel.com/rhino/5/help/en-us/popup_moreinformation/continuity_descriptions.htm G1 continuity so that MergeSrf can be employed
# - Bezier patches apparently better suited to minimal/tent surfaces.
# - Look into existing plugins, Weaverbird, Resurf, Evolute, Membrane, Kangaroo
# - When working with NURBS Surfaces with degree curves > 1 we'll have to split each patch in 2 to avoid the averaged curvature through 0. Have tried various approaches to this, not yet sure which is best. Or we locate that point  [3.1 CP2 Example](https://pdfs.semanticscholar.org/d02a/1aa2dbff30d6492d8085bdd760123bd54bf5.pdf) and add weight to it so that the surface creases sharply at this pnt.
# - Intersection
# http://developer.rhino3d.com/api/RhinoCommon/html/M_Rhino_Geometry_Intersect_Intersection_CurveSelf.htm
#  http://developer.rhino3d.com/api/RhinoCommon/html/N_Rhino_Geometry_Intersect.htm
# http://developer.rhino3d.com/api/RhinoCommon/html/Methods_T_Rhino_Geometry_Intersect_Intersection.htm
# http://developer.rhino3d.com/api/RhinoCommon/html/M_Rhino_Geometry_Intersect_Intersection_SurfaceSurface.htm
# http://developer.rhino3d.com/api/RhinoCommon/html/T_Rhino_Geometry_NurbsSurface.htm
#
# http://developer.rhino3d.com/api/RhinoCommon/html/M_Rhino_Geometry_NurbsSurface_CreateFromCorners_2.htm

[
    ["A", 0, 0, -5.5511151231257827e-17, 0],
    ["A", 0, 0, -5.5511151231257827e-17, 0],
    ["A", 0, 1, -5.5511151231257827e-17, 0],
    ["A", 0, 1, -5.5511151231257827e-17, 0],
    ["A", 0, 2, -5.5511151231257827e-17, 0],
    ["A", 0, 2, -5.5511151231257827e-17, 0],
    ["A", 1, 0, -5.5511151231257827e-17, 0],
    ["A", 1, 0, -5.5511151231257827e-17, 0],
    ["A", 1, 1, -5.5511151231257827e-17, 0],
    ["A", 1, 1, -5.5511151231257827e-17, 0],
    ["A", 1, 2, -5.5511151231257827e-17, 0],
    ["A", 1, 2, -5.5511151231257827e-17, 0],
    ["A", 2, 0, -5.5511151231257827e-17, 0],
    ["A", 2, 0, -5.5511151231257827e-17, 0],
    ["A", 2, 1, -5.5511151231257827e-17, 0],
    ["A", 2, 1, -5.5511151231257827e-17, 0],
    ["A", 2, 2, -5.5511151231257827e-17, 0],
    ["A", 2, 2, -5.5511151231257827e-17, 0]
]

[
    [1.0, 0.0, 0.0],
    [1.0, 0.0, 0.0],
    [1.0, 0.0, -0.0],
    [1.0, 0.0, -0.0],
    [1.0, -0.0, 0.0],
    [1.0, -0.0, 0.0],

    [-0.50000000000000044, 0.0, 0.86602540378443837],
    [-0.50000000000000044, 0.0, 0.86602540378443837],
    [-0.50000000000000044, 0.0, 0.86602540378443837],
    [-0.50000000000000044, 0.0, 0.86602540378443837],
    [-0.50000000000000044, -0.0, 0.86602540378443837],
    [-0.50000000000000044, -0.0, 0.86602540378443837],

    [-0.49999999999999922, 0.0, -0.86602540378443915],
    [-0.49999999999999922, 0.0, -0.86602540378443915],
    [-0.49999999999999922, 0.0, -0.86602540378443915],
    [-0.49999999999999922, 0.0, -0.86602540378443915],
    [-0.49999999999999922, -0.0, -0.86602540378443915],
    [-0.49999999999999922, -0.0, -0.86602540378443915]
]

# Here we can group all patches passing through these 0 points

# for k1 in RngK:
#     # Example A
#     # for k2 in RngK:
#     #    for k3 in 1, 2:
#
#     # Example B
#     for k2 in range(n * 2):
#             for a in RngA:
#                 for b in RngB:
#
# - Is it possible to order these for visual continuity. Ie. if we can order them in a way that we can create n groups and loft, or brep, or merge a "PHASES" "patch" or build a tensile surface ie kangaroo.
#



Log = []

I = complex(0.0, 1.0)  # equiv to `cmath.sqrt(-1)`
n = 7
Alpha = float(0.7) * math.pi
Scale = float(100.0)

def U1(a, b):
    m1 = cmath.exp(complex(a, b))
    m2 = cmath.exp(complex(-a, -b))
    return (m1 + m2) * 0.5


def U2(a, b):
    m1 = cmath.exp(complex(a, b))
    m2 = cmath.exp(complex(-a, -b))
    return (m1 - m2) * 0.5


def Z1(a, b, n, k):
    u1 = U1(a, b) ** (2.0 / n)
    m1 = cmath.exp(I * (2.0 * pi * k) / (n * 0.5))
    return m1 * u1


def Z2(a, b, n, k):
    u2 = U2(a, b) ** (2.0 / n)
    m2 = cmath.exp(I * (2.0 * pi * k) / (n * 0.5))
    return m2 * u2


def Calculate(n, alpha, k1, k2, a, b):
    '''
    Returns:
        R3 coordinates (x, y, z) as complex

    Parameters:
        n : int
        alpha : float
        k1 : float
        k2 : float
        a : float
        b : float
    '''
    z1 = Z1(a, b, n, k1)
    z2 = Z2(a, b, n, k2)

    point = (z1.real), (z2.real), (cos(alpha) * z1.imag + sin(alpha) * z2.imag)

    if z1.real == 0 or z2.real == 0:
        # Log.append(["A", k1, k2, a, b])
        Log.append(point)

    # else:
        # Log.append(["B", a])
        # rs.AddPoint(Point3d(*point))
        # rs.AddTextDot(
        #     str(c) + '[' + str(k1) + ',' + str(k2) + ']',
        #     Point3d(*point)
        # )

    return point

def Point(*args):
    coords = map(lambda i: i * Scale, Calculate(n, Alpha, *args))
    return Point3d(*coords)

def CreateInterpolatedCurve(points):
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

def __Split():
    U = int(11)
    V = int(11)
    MinU = -1
    MaxU = 1
    StepU = (math.fabs(MaxU - MinU) / float(U - 1))

    MinV = 0
    MaxV = float(math.pi / 2)
    StepV = (math.fabs(MaxV - MinV) / float(V - 1))

    RngK = rs.frange(0, n * 2 - 1, 1)
    RngU = rs.frange(MinU, MaxU, StepU)
    RngV = rs.frange(MinV, MaxV, StepV)

    Points = Point3dList()
    CntU = float(0)
    CntV = float(0)
    SrfCnt = float(0)

    Domains = []

    for i, k1 in enumerate(RngK):
        for i, k2 in enumerate(RngK):
            Domains.append([k1, k2])

    for domain in Domains:
        k1, k2 = domain

        # Crvs = CurveList()
        # CrvA = []
        # CrvB = []
        # CrvC = []
        # CrvD = []
        #
        # for a in RngU:
        #     if a == RngU[0]:
        #         CrvA = CreateInterpolatedCurve(map(lambda b: Point(k1, k2, a, b), RngV))
        #     if a == RngU[-1]:
        #         CrvC = CreateInterpolatedCurve(map(lambda b: Point(k1, k2, a, b), RngV))
        #
        #     for b in RngV:
        #         if b == RngV[0]:
        #             CrvB.append(Point(k1, k2, a, b))
        #         if b == RngV[-1]:
        #             CrvD.append(Point(k1, k2, a, b))
        #
        #
        # Crvs.Add(CrvA)
        # Crvs.Add(CrvB)
        # Crvs.Add(CrvC)
        # Crvs.Add(CrvD)
        #
        # surf, err = NurbsSurface.CreateNetworkSurface(
        #     Crvs,  # IEnumerable<Curve> curves,
        #     0,  # int continuity along edges, 0 = loose, 1 = pos, 2 = tan, 3 = curvature
        #     0.0001,  # double edgeTolerance,
        #     0.1,  # double interiorTolerance,
        #     1.0  # double angleTolerance,
        # )
        #
        # doc.Objects.AddSurface(surf)

        Points = Point3dList()
        CntU = float(0)
        CntV = float(0)

        for a in RngU:
            CntV = float(0)

            for b in RngV:
                Points.Add(Point(k1, k2, a, b))
                CntV += 1
            CntU += 1

        surf = NurbsSurface.CreateFromPoints(
            Points,
            round(CntU),
            round(CntV),
            3,
            3
        )

        doc.Objects.AddSurface(surf)

def __R():
    U = int(11)
    V = int(11)
    MinU = -1
    MaxU = 1
    StepU = math.fabs(MaxU - MinU) / float(U - 1)

    MinV = 0
    MaxV = float(math.pi / 2)
    StepV = math.fabs(MaxV - MinV) / float(V - 1)


    RngK = rs.frange(0, n - 1, 1)
    RngU = rs.frange(MinU, MaxU, StepU)
    RngV = rs.frange(MinV, MaxV, StepV)

    Points = Point3dList()
    CntU = float(0)
    CntV = float(0)
    SrfCnt = float(0)

    # This allows us to control the order rather than jumping around
    # Domains = [[0,0], [1,0], [2,0]]
    # Domains = [[0,0], [0,1], [0,2], [1,2], [1, 1], [1,0], [2,0], [2,1], [2,2]]
    Domains = [
        # [0,0],
        # [1,0],
        # [2,0],

        # [0,0],
        # [1,1],
        # [2,1],

        # [0,2],
        # [1,2],
        # [2,2],

        # [0,0],
        # [1,1],
        # [2,2]

        # [2,0],
        # [2,1],
        [2,2]
    ]
    # for i, e in enumerate(RngK):
    #     Domains.append([e, e])
    #     try:
    #         Domains.append([e, RngK[i + 1]])
    #     except:
    #         pass

    # for a in RngU[0], RngU[len(RngU) / 2], RngU[-1]:
    #     for b in RngV:
    #         point = Point(k1, k2, a, b)
    #         rs.AddPoint(point)
    # for a in RngU:
    #     for b in RngV[0], RngV[len(RngV) / 2], RngV[-1]:
    #         point = Point(k1, k2, a, b)
    #         rs.AddPoint(point)

    for domain in Domains:
        k1, k2 = domain

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
                # Points = []
                # for b in RngV:
                #     point = Point(k1, k2, a, b)
                #     Points.append(point)

                # rs.AddInterpCurve(map(lambda b: Point(k1, k2, a, b), RngV))
                CrvA1 = CreateInterpolatedCurve(map(lambda b: Point(k1, k2, a, b), RngV))
            if a == RngU[len(RngU) / 2]:
                # rs.AddInterpCurve(map(lambda b: Point(k1, k2, a, b), RngV))
                CrvC1 = CreateInterpolatedCurve(map(lambda b: Point(k1, k2, a, b), RngV))
                CrvA2 = CrvC1
            if a == RngU[-1]:
                # rs.AddInterpCurve(map(lambda b: Point(k1, k2, a, b), RngV))
                CrvC2 = CreateInterpolatedCurve(map(lambda b: Point(k1, k2, a, b), RngV))

            for b in RngV:
                # point = Point(k1, k2, a, b)
                if b == RngV[0]:
                    # CrvStart.append(point)
                    if len(CrvB1) <= 5: # <= (len(RngV) / 2)
                        CrvB1.append(Point(k1, k2, a, b))
                    if len(CrvB1) >= 5: # <= (len(RngV) / 2)
                        CrvB2.append(Point(k1, k2, a, b))
                # if b == RngV[len(RngV) / 2]:
                #     CrvMid.append(point)
                if b == RngV[-1]:
                    # CrvEnd.append(point)
                    if len(CrvD1) <= 5: # <= (len(RngV) / 2)
                        CrvD1.append(Point(k1, k2, a, b))
                    if len(CrvD1) >= 5: # <= (len(RngV) / 2)
                        CrvD2.append(Point(k1, k2, a, b))

        # rs.AddPolyline(CrvStart)
        # rs.AddPolyline(CrvMid)
        # rs.AddPolyline(CrvEnd)

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

        # return


def __Runt():
    U = int(11) # 5 knots and 3 degrees works nicely with n = 3, Bit too jagged though
    V = int(11)
    MinU = -1
    MaxU = 1
    StepU = math.fabs(MaxU - MinU) / float(U - 1)

    MinV = 0
    MaxV = float(math.pi / 2)
    StepV = math.fabs(MaxV - MinV) / float(V - 1)

    RngK = rs.frange(0, n - 1, 1)
    RngU = rs.frange(MinU, MaxU, StepU)
    RngV = rs.frange(MinV, MaxV, StepV)

    for k1 in RngK:
        for k2 in RngK:
            Points = Point3dList()
            CntU = float(0)
            CntV = float(0)

            for i in range(0, U / 2 + 1):
                a = RngU[i]
                CntV = float(0)

                for b in RngV:
                    Points.Add(Point(k1, k2, a, b))
                    CntV += 1
                CntU += 1

            surf2 = NurbsSurface.CreateFromPoints(
                Points,
                round(CntU),
                round(CntV),
                3,
                3
            )

            Points2 = Point3dList()
            CntU2 = float(0)
            CntV2 = float(0)

            for i in range(U / 2, U):
                a = RngU[i]
                CntV2 = float(0)

                for b in RngV:
                    Points2.Add(Point(k1, k2, a, b))
                    CntV2 += 1
                CntU2 += 1

            surf3 = NurbsSurface.CreateFromPoints(
                Points2,
                round(CntU2),
                round(CntV2),
                3,
                3
            )

            doc.Objects.AddSurface(surf2)
            doc.Objects.AddSurface(surf3)


def __ParametricPlot3D():
    n = 3
    E = cmath.e
    I = cmath.sqrt(-1)

    def u1(a, b):
        return complex(0.5 * (E ** (a + I * b) + E ** (-a - I * b)))

    def u2(a, b):
        return complex(0.5 * (E ** (a + I * b) - E ** (-a - I * b)))

    def z1k(a, b, n, k):
        return complex(E ** (k * 2.0 * pi * I / n) * u1(a, b) ** (2.0 / n))

    def z2k(a, b, n, k):
        return complex(E ** (k * 2.0 * pi * I / n) * u2(a, b) ** (2.0 / n))

    x = float(0)  # Offset
    y = float(0)  # Offset
    z = float(0)  # Offset
    Alpha = float(0.3)
    t = math.pi / float(4)
    alpha = Alpha - t
    # alpha = Alpha * math.pi
    Scale = float(100.0)

    # Read up on NURBS point coint and surface degree are related
    # 11, 82
    U = int(11)  # Why does 11 work
    V = int(11)
    MinU = -1
    MaxU = 1
    StepU = math.fabs(MaxU - MinU) / float(U - 1)

    MinV = 0
    MaxV = float(math.pi / 2)
    StepV = math.fabs(MaxV - MinV) / float(V - 1)


    RngK = rs.frange(0, n - 1, 1)
    RngU = rs.frange(MinU, MaxU, StepU)
    RngV = rs.frange(MinV, MaxV, StepV)

    # a = 1
    # b = 1
    # k1 = 1
    # k2 = 3
    # X = z1k(a, b, n, k1).real + x
    # Y = z2k(a, b, n, k2).real + y
    # Z = (cos(alpha) * z1k(a, b, n, k1).imag) + (sin(alpha) * z2k(a, b, n, k2).imag) + z

    Points = Point3dList()
    CntU = float(0)
    CntV = float(0)
    SrfCnt = float(0)

    for k1 in RngK:
        for k2 in RngK:
            Points = Point3dList()
            CntU = float(0)
            CntV = float(0)

            for a in RngU:
                CntV = float(0)

                for b in RngV:
                    x = z1k(a, b, n, k1).real
                    y = z2k(a, b, n, k2).real
                    z = (cos(alpha) * z1k(a, b, n, k1).imag) + (sin(alpha) * z2k(a, b, n, k2).imag)
                    point = Point3d(x * Scale, y * Scale, z * Scale)
                    Points.Add(point)
                    # rs.AddPoint(point)

                    CntV += 1

                    # We need to patch this junction up,
                    # Problem is its in the middle of the U edge curve.
                    # Fixed when U Degree set to 1.
                    # if a == RngU[U / 2] and b == RngV[0] or a == RngU[U / 2] and b == RngV[-1]:
                        # rs.AddTextDot('*', point)

                CntU += 1

            # When U and V degree differ, a polysurface will be created
            surf2 = NurbsSurface.CreateFromPoints(
                Points,
                round(CntU),  # Points U
                round(CntV),  # Points V
                2,  # Surface Degree U
                2   # Surface Degree V
            )

            # Offset each point in cases where we want to output two complete surfaces
            # POffset = Point3dList()
            # for pt in Points:
            #     x = pt.X + 1000
            #     y = pt.Y + 1000
            #     z = pt.Z + 1000
            #     POffset.Add(Point3d(x, y, z))


            # surf1 = NurbsSurface.CreateThroughPoints(
            #     Points,
            #     CntU,
            #     CntV,
            #     1,
            #     1,
            #     False,  # Closed U
            #     False   # Closed V
            # )

            # print CntU, Springer[1]
            # print surface.PointAt(0, 0).Weight
            # pt = surface.Points.GetControlPoint(CntU, Springer[1])
            # print pt.Weight

            # doc.Objects.AddSurface(surf1)
            # SrfCnt += 1
            # if k1 == RngK[0]: doc.Objects.AddSurface(surf2)
            doc.Objects.AddSurface(surf2)
            print 'KU', surf2.KnotsU
            # print 'KV', surf2.KnotsV.__dict__
            return
        # return


def ParametricPlot3D():
    n = 2  # n
    Alpha = 0.3 * pi  # deg * pi
    Step = 0.1  # step
    Scale = float(100)  # scale
    MinA = -1
    MaxA = 1
    MinB = 0
    MaxB = pi / 2
    StepA = Step
    StepB = MaxB * Step
    RngK = range(n)
    D1 = rs.frange(MinA, MaxA, StepA)
    D2 = rs.frange(MinB, MaxB, StepB)

    # n = 2  # n
    # Alpha = 1.0 * math.pi  # deg * pi
    # Scale = float(100)  # scale
    # U = int(100)
    # V = int(100)
    # # R = float(2)
    # # T = float(1)
    # MaxU = float(1)
    # MinU = -MaxU
    # MaxV = float(math.pi / 2)
    # MinV = 0
    # StepU = math.fabs(MaxU - MinU) / float(U - 1)
    # StepV = math.fabs(MaxV - MinV) / float(V - 1)
    # RngK = range(n)
    # D1 = rs.frange(MinU, MaxU, StepU)
    # D2 = rs.frange(MinV, MaxV, StepV)

    # Points = Point3dList()
    # CntU = float(0)
    # CntV = float(0)

    for k1 in RngK:
        for k2 in RngK:
            Points = Point3dList()
            CntU = float(0)
            CntV = float(0)

            for a in D1:
                CntV = 0

                for b in D2:
                    x, y, z = map(lambda i: i * Scale, Calculate(n, Alpha, k1, k2, a, b))
                    point = Point3d(x, y, z)
                    Points.Add(point)
                    CntV += 1
                CntU += 1

            surface = NurbsSurface.CreateFromPoints(
                Points,
                round(CntU),  # Points U
                round(CntV),  # Points V
                1,  # Surface Degree U
                2   # Surface Degree V
            )

            doc.Objects.AddSurface(surface)



def Run():
    # ParametricPlot3D()
    # __ParametricPlot3D()
    __Runt()
    print json.dumps(Log)
    # __R()
    # __Split()
    doc.Views.Redraw()
