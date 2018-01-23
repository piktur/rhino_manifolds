import cmath
from math import cos, sin, pi

# n = 3
# E = cmath.e
# I = cmath.sqrt(-1)
#
# def u1(a, b):
#     return complex(0.5 * (E ** (a + I * b) + E ** (-a - I * b)))
#
# def u2(a, b):
#     return complex(0.5 * (E ** (a + I * b) - E ** (-a - I * b)))
#
# def z1k(a, b, n, k):
#     return complex(E ** (k * 2.0 * pi * I / n) * u1(a, b) ** (2.0 / n))
#
# def z2k(a, b, n, k):
#     return complex(E ** (k * 2.0 * pi * I / n) * u2(a, b) ** (2.0 / n))
#
# x = float(0)  # Offset
# y = float(0)  # Offset
# z = float(0)  # Offset
# Alpha = float(0.3)
# t = math.pi / float(4)
# alpha = Alpha - t
# # alpha = Alpha * math.pi
# a = 1
# b = 1
# k1 = 1
# k2 = 3
# X = z1k(a, b, n, k1).real + x
# Y = z2k(a, b, n, k2).real + y
# Z = (cos(alpha) * z1k(a, b, n, k1).imag) + (sin(alpha) * z2k(a, b, n, k2).imag) + z

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
