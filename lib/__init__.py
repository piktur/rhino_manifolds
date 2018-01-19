import rhinoscriptsyntax as rs
import events
import export
import utility
import calabi
import helicoid
import alt

from Rhino.Geometry import Point3d, NurbsSurface, ControlPoint
from scriptcontext import doc

reload(calabi)
reload(alt)

rs.EnableRedraw(True)

if __name__ == '__main__':
    # calabi.Run()
    # helicoid.Run()
    alt.Run()
