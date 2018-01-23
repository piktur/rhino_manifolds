'''
Replaces Grasshopper workflow -- execute via `RunPythonScript`

[](http://www.tanjiasi.com/surface-design/)
[](http://www.food4rhino.com/app/calabi-yau-manifold)
[Python Standard Library - math](https://docs.python.org/2/library/math.html)
[Python Standard Library - cmath](https://docs.python.org/2/library/cmath.html)

TOOD Assign elements to separate layers
'''
import os
from scriptcontext import doc
# from rhinoscriptsyntax import GetBoolean, GetInteger, GetReal
import rhinoscriptsyntax as rs
import utility
import builder
import export
from export import fname
import manifold
import layers

reload(utility)
reload(builder)
reload(export)
reload(manifold)
reload(layers)


def GetUserInput():
    n = rs.GetInteger('n', 3, 1, 10)
    Alpha = rs.GetReal('Degree', 1.0, 0.0, 1.0)
    Density = rs.GetReal('Density', 0.1, 0.01, 0.4)
    Scale = rs.GetInteger('Scale', 100, 1, 100)
    Offset = rs.GetInteger('Offset', 0, 0, 300)
    Offset = (Offset, Offset)
    Builder = rs.GetInteger('Type', 4, 1, 5)

    return n, Alpha, Density, Scale, Offset, Builder


def GenerateGrid(density=0.1, scale=100, type=4):
    '''
    Generate 10 x 10 grid
    '''
    arr = []
    offset = scale * 3
    originY = 0
    originX = 0
    x = originX
    y = originY
    alpha = rs.frange(0.1, 1.0, 0.1)

    for n in rs.frange(1, 10, 1):
        x = originX + (n * offset)
        y = originY

        for a in alpha:
            arr.append(manifold.Manifold(int(n), a, density, scale, (x, y), type))
            y += offset

        originY = 0
        originX += offset

    for obj in arr:
        obj.Build()
        doc.Views.Redraw()


def Batch(dir, density=0.1, scale=100, type=4):
    queue = {}
    offset = scale * 3
    alpha = rs.frange(0.1, 1.0, 0.1)

    for n in rs.frange(2, 10, 1):
        for a in alpha:
            out = export.fname('3dm', os.path.join(dir, str(n)), 'CY', str(int(a * 10)))
            queue[out] = manifold.Manifold(int(n), a, density, scale, (0, 0), type)

    return queue


def Run(*args):
    if rs.ContextIsRhino:  # rs.ContextIsGrasshopper
        args = GetUserInput()

    manifold.Manifold(*args).Build()
    doc.Views.Redraw()


def Make2D():
    layers.Build()
