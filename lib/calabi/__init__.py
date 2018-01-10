'''

Replaces Grasshopper workflow -- execute via `RunPythonScript`

[](http://www.tanjiasi.com/surface-design/)
[](http://www.food4rhino.com/app/calabi-yau-manifold)
[Python Standard Library - math](https://docs.python.org/2/library/math.html)
[Python Standard Library - cmath](https://docs.python.org/2/library/cmath.html)

TOOD Assign elements to separate layers
'''

from scriptcontext import doc
# from rhinoscriptsyntax import GetBoolean, GetInteger, GetReal
import rhinoscriptsyntax as rs
import utility
import builder
import export
import manifold

reload(utility)
reload(builder)
reload(export)
reload(manifold)


def Run():
    n = rs.GetInteger('n', 3, 1, 10)
    Alpha = rs.GetReal('Degree', 1.0, 0.0, 1.0)
    Density = rs.GetReal('Density', 0.1, 0.01, 0.4)
    Scale = rs.GetInteger('Scale', 100, 1, 100)
    Builder = rs.GetInteger('Type', 5, 1, 5)
    manifold.Manifold(n, Alpha, Density, Scale, Builder).Build()

    doc.Views.Redraw()


rs.EnableRedraw(True)

if __name__ == '__main__':
    Run()
