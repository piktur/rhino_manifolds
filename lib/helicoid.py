import cmath
import math
from scriptcontext import doc
import rhinoscriptsyntax as rs
from Rhino.Geometry import Point3d
from Rhino.Geometry import NurbsSurface
from Rhino.Collections import Point3dList


def Run():
    U = int(100)
    V = int(100)
    R = float(3)
    T = float(2)
    Scale = float(100)
    MaxU = float(math.pi * 2)  # float(max(D1))
    MinU = -MaxU  # float(min(D1))
    MaxV = float(math.pi)  # float(max(D2))
    MinV = -MaxV  # float(min(D2))
    StepU = math.fabs(MaxU - MinU) / float(U - 1)
    StepV = math.fabs(MaxV - MinV) / float(V - 1)
    D1 = rs.frange(MinU, MaxU, StepU)
    D2 = rs.frange(MinV, MaxV, StepV)

    Points = Point3dList()
    CntU = float(0)
    CntV = float(0)
    PosU = MinU
    PosV = MinV

    while PosU <= (MaxU + StepU):
        PosV = MinV
        CntV = 0
        while PosV <= (MaxV + StepV):
            x = float(PosU * math.cos(T * PosV))
            y = float(PosU * math.sin(T * PosV))
            z = float(R * PosV)
            point = Point3d(x * Scale, y * Scale, z * Scale)
            Points.Add(point)
            PosV += StepV
            CntV += 1
        PosU += StepU
        CntU += 1

    surface = NurbsSurface.CreateFromPoints(
        Points,
        round(CntU),  # Points U
        round(CntV),  # Points V
        2,  # Surface Degree U
        2   # Surface Degree V
    )


    doc.Objects.AddSurface(surface)
    doc.Views.Redraw()
