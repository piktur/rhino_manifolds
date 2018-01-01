import math, cmath
import Rhino.Geometry.Point3d as rhp3

I = complex(0.0, 1.0)
n = int(DimensionJIASI)
Alpha = (float(Rotation) + 1) * math.pi
Points = []

def qrange(start, stop = None, step = 1):
    # if start is missing it defaults to zero, somewhat tricky
    start, stop = (0, start) if stop is None else (start, stop)
    # allow for decrement
    while start > stop if step < 0 else start < stop:
        yield start # makes this a generator for new start value
        start += step

def Complex_u1(a, b):
    m1 = complex(a, b)
    m2 = complex(-a, -b)
    m1Exp = cmath.exp(m1)
    m2Exp = cmath.exp(m2)
    m1Exp_Plus_m2Exp = m1Exp + m2Exp
    return m1Exp_Plus_m2Exp * 0.5

def Complex_u2(a, b):
    m1 = complex(a, b)
    m2 = complex(-a, -b)
    m1Exp = cmath.exp(m1)
    m2Exp = cmath.exp(m2)
    m1Exp_Plus_m2Exp = m1Exp + m2Exp
    return m1Exp_Plus_m2Exp * 0.5

def Complex_z1(a, b, n, k):
    u_1 = Complex_u1(a, b) * (2.0 / n)
    m_1 = I * ((2.0 * math.pi * k) / n)
    m1 = cmath.exp(m_1)
    return m1 * u_1

def Complex_z2(a, b, n, k):
    u_2 = Complex_u2(a, b) * (2.0 / n)
    m_2 = I * ((2.0 * math.pi * k) / n)
    m2 = cmath.exp(m_2)
    return m2 * u_2

def ParametricPlot3D(step = 0.1):
    maxB = math.pi / 2 + step
    for k1 in range(n):
        for k2 in range(n):
            for a in qrange(-1, 1, step):
                for b in qrange(0, maxB, step):
                    z1 = Complex_z1(a, b, n, k1)
                    z2 = Complex_z2(a, b, n, k2)
                    x_new = z1.real
                    y_new = z2.real
                    z_new = math.cos(Alpha) * z1.imag + math.sin(Alpha) * z2.imag
                    Points.append(rhp3(x_new, y_new, z_new))
    return Points

a = ParametricPlot3D()
