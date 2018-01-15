import cmath
import math
from math import cos, sin, pi
from scriptcontext import doc
import rhinoscriptsyntax as rs
from Rhino.Geometry import Point3d
from Rhino.Geometry import NurbsSurface
from Rhino.Collections import Point3dList


I = complex(0.0, 1.0)


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
    m1 = cmath.exp(I * ((2.0 * pi * k) / n))
    return m1 * u1


def Z2(a, b, n, k):
    u2 = U2(a, b) ** (2.0 / n)
    m2 = cmath.exp(I * ((2.0 * pi * k) / n))
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

    return (z1.real), (z2.real), (cos(alpha) * z1.imag + sin(alpha) * z2.imag)

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
    Scale = float(100.0)

    U = int(10)
    V = int(10)
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

                    if a == RngU[5] and b == RngV[0] or a == RngU[5] and b == RngV[-1]:
                        rs.AddTextDot('*', point)

                    Points.Add(point)
                    CntV += 1

                CntU += 1

            surface = NurbsSurface.CreateFromPoints(
                Points,
                round(CntU),  # Points U
                round(CntV),  # Points V
                2,  # Surface Degree U
                2   # Surface Degree V
            )
            doc.Objects.AddSurface(surface)


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
    __ParametricPlot3D()
    doc.Views.Redraw()
