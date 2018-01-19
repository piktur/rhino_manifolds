import System.Guid
import System.Drawing
from scriptcontext import doc
import rhinoscriptsyntax as rs

# Layers
# - `DupBorder` from Srf
# - `Intersection`
# - `DupBorder` from PolySrf
# - `Sillhouette` from PolySrf
# - `Extract Wiremesh` from PolySrf
# - `Extract Isocurves`
#
# - From `Perspective` position camera and  Select
#     PolySrf
#     Wireframe
#     Intersections
#
# Or
#     PolySrf
#     Border
#     Edges
#     Intersections
#
# - [`Make2D`](http://docs.mcneel.com/rhino/5/help/en-us/commands/make2d.htm) select "Current View" and select relevant layers lines etc to display. NOTE When using Make2d create a new layer for 2D and assign 2D Objects to it.
# Otherwise display will be linked to the source layer.
#
# Swith to Top View
# Hide all layers but 2D
# `SelCrv`
# `File > Export Selected`.
# Use *.ai. Experiment with scale.
# Use CMYK Save.

layers = [
    'Srf',
    'Edges',  #
    'Intersections',  # Demarcate intersesctions
    'PolySrf',  # Copy patches to new layer and Join
    'Border',  # Demarcate Border
    'Silhouette',  # Weird artifacts across surface
    'Wireframe',   # Tweak Isocurve count
    '2D'  # Project to 2D plane
]

# Data
# Attributes
# Render Meshes
# Grips
# Analysis models
# **wireframe curves
# selection flags
# state flags
# history
#
# Attributes
# **UUID
# NAme
# **Layer
# **Group list
# Url
# **Material source and index
# **Rendering attributes
# **colour source and value
# **isocurve density
# **linetype source & style
# **display mode
# arrowhead
# plotcolor source and value
# plotweight sourcce and value
#
# Object Geometry
# Geometry
# BoundingBox
# Sub objects
# **Type

def Build():


    # # doc.Views
    # # doc.Views.ActiveView.ActiveViewport

    # # rhino_object = rhutil.coercerhinoobject(surface_id, True, True)
    return
    for layer in layers:
        if not rs.IsLayer(layer):
            # layer = doc.Layers.Add(e, System.Drawing.Color.Black)
            layer = rs.AddLayer(layer, System.Drawing.Color.Black)
            rs.LayerVisible(layer, False)

    # layerNames = rs.LayerNames()

    surfaces = rs.ObjectsByType(rs.filter.surface | rs.filter.polysurface, True)

    rs.Command('Intersection')
    Intersections = rs.LastCreatedObjects(True)
    for id in Intersections:
        rs.ObjectLayer(id, 'Intersections')

    for id in surfaces:
        rs.SurfaceIsocurveDensity(id, 10)

    # rs.UnselectObjects(surfaces)
    rs.Command('ExtractWireframe') # + ','.join(map(lambda e: e.ToString(), surfaces))
    Wireframe = rs.LastCreatedObjects(True)
    for id in Wireframe:
        rs.ObjectLayer(id, 'Wireframe')

    rs.Command('DupBorder')
    Border = rs.LastCreatedObjects(True)
    for id in Border:
        rs.ObjectLayer(id, 'Border')

    rs.Command('Silhouette')
    Silhouette = rs.LastCreatedObjects(True)
    for id in Silhouette:
        rs.ObjectLayer(id, 'Silhouette')

    # copy = rs.CopyObjects(surfaces)
    # object = rs.coercerhinoobject(PolySrf, True, True)
    # PolySrf = rs.JoinSurfaces(copy)
    # print PolySrf
    # return
    # doc.Objects.Attributes.LayerIndex = layer(object, rs.__getlayer('PolySrf', True))
    #
    # rs.Command('Make2D')
    #
    # # # Copy the objects
    # # newObjectIds = rs.CopyObjects(objectIds)
    # # [rs.ObjectLayer(object, rs.__getlayer('PolySrf', True))
    # # [rs.ObjectLayer(id, layer) for id in newObjectIds]
    # # rs.SelectObjects( newObjectIds )

    # if Surfaces:
    #     rs.EnableRedraw(False)
    #     for id in Surfaces:
    #         doc.Objects.ModifyAttributes(id, )
    #         print obj.Attributes

    # for object in selected:
    #     object.Attributes.LayerIndex = layer
    #     object.CommitChanges()

    # doc.Views.Redraw()
