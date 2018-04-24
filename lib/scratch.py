import rhinoscriptsyntax as rs
import json
import util
from scriptcontext import doc, sticky
from Rhino.Geometry import Curve, Point3d
from Rhino.Collections import Point3dList, CurveList
from Rhino.Geometry import Point3d, Brep, BrepFace, Surface, NurbsSurface, Interval, Curve, Intersect

rs.EnableAutosave(False)
