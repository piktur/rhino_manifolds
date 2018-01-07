import cmath
from math import cos, sin, pi

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
