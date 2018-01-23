import System.Guid
import System.Drawing
from scriptcontext import doc
import rhinoscriptsyntax as rs
from Rhino.Geometry import Vector3d, Plane, Point3d, Brep


layers = [
    'Srf',
    'Intersections',    # Perform before `Join`. `Intersection` Curves
    'PolySrf',          # `Join` Patches
    'Border::All',      # `Join` + `DupBorder`
    'Border::Outer',    # Perform before `Join`. `SelAll` Patches + `DupBorder`
    'Edges',            # Perform before `Join`. `SelAll` Patches + `DupBorder`
    'Silhouette',       # `Join` + `Silhouette`. Weird artifacts across surface
    'Wireframe',        # Set `SurfaceIsocurveDensity` then `Join` + `ExtractWireframe`.
    'RenderMesh',       # Set `SurfaceIsocurveDensity` then `Join` + `ExtractRenderMesh`.
    '2D'                # Project to 2D plane
]


def Build():
    # doc.Views.ActiveView.ActiveViewport
    # rhino_object = rhutil.coercerhinoobject(surface_id, True, True)
    # layerNames = rs.LayerNames()

    # for object in selected:
    #     object.Attributes.LayerIndex = layer
    #     object.CommitChanges()

    # doc.Objects.ModifyAttributes(id, )
    # print obj.Attributes

    # rs.EnableRedraw(False)
    print doc.Linetypes

    Layers()
    Patches()
    Intersect()
    Border()
    Silhouette()
    Wireframe()

    rs.EnableRedraw(True)
    doc.Views.Redraw()


def Layers():
    for layer in layers:
        if not rs.IsLayer(layer):
            # layer = doc.Layers.Add(e, System.Drawing.Color.Black)
            layer = rs.AddLayer(layer, System.Drawing.Color.Black)
            rs.LayerVisible(layer, False)


def Patches():
    # surfaces = rs.ObjectsByType(rs.filter.surface | rs.filter.polysurface, True)
    # surfaceIds = ','.join(map(lambda e: e.ToString(), surfaces))
    # Patches = rs.ObjectsByType(rs.filter.surface | rs.filter.polysurface, True)
    Patches = doc.Objects.FindByLayer('Default')
    PatchesIds = rs.CopyObjects(Patches)
    PolySrf = rs.JoinSurfaces(PatchesIds)  # rs.Command('Join')
    rs.ObjectLayer(PolySrf, 'PolySrf')


def Intersect():
    # rs.Command('SelSrf')
    rs.ObjectsByType(rs.filter.surface, True)
    rs.Command('_Intersect')
    # Intersections = rs.LastCreatedObjects(True)
    for id in rs.ObjectsByType(rs.filter.curve, True):
        rs.ObjectLayer(id, 'Intersections')


def Border():
    PolySrf = doc.Objects.FindByLayer('PolySrf')[0].Id.ToString()

    # rs.Command('DupBorder')
    # Border = rs.LastCreatedObjects(True)
    Edges = rs.DuplicateEdgeCurves(PolySrf, True)
    Border = rs.DuplicateSurfaceBorder(PolySrf, 2)

    for id in Edges:
        rs.ObjectLayer(id, 'Border::All')

    for id in Border:
        rs.ObjectLayer(id, 'Border::Outer')


def Silhouette():
    return
    # doc.Objects.FindByLayer('PolySrf')
    # rs.Command('Silhouette')
    # Silhouette = rs.LastCreatedObjects(True)
    # rs.ObjectLayer(Silhouette, 'Silhouette')


# See Patch topology example https://bitbucket.org/snippets/kunst_dev/Kyzqyp
#
#     for id in surfaces:
#         U, V = rs.SurfaceKnotCount(id)
#         point = # Some point on the surface
#         rs.ExtractIsoCurve(id, point, 0 = U, 1 = V, 2 = Both):
def Wireframe():
    for i in range(-1, 10, 1):
        PolySrf = doc.Objects.FindByLayer('PolySrf')[0].Id.ToString()
        # rs.SurfaceIsocurveDensity(PolySrf, i)
        rhino_object = rs.coercerhinoobject(PolySrf, True, True)
        print rhino_object
        # if not isinstance(rhino_object, Rhino.DocObjects.BrepObject):
        #     return scriptcontext.errorhandler()
        rc = rhino_object.Attributes.WireDensity
        rhino_object.Attributes.WireDensity = i
        rhino_object.CommitChanges()
        doc.Views.Redraw()

        layer = 'Wireframe::' + str(i)
        if not rs.IsLayer(layer):
            layer = rs.AddLayer(layer, System.Drawing.Color.Black)
        rs.LayerVisible(layer, False)
        rs.CurrentLayer(layer)

        # doc.Objects.FindByLayer('PolySrf', True)
        rs.ObjectsByType(rs.filter.polysurface, True)

        # + PolySrf
        rs.Command('_SelPolySrf')

        rs.Command(
            '_ExtractWireframe '
            + PolySrf
            + ' OutputLayer=Current'
            + ' GroupOutput=No'
        )
        rs.Command('_SelPolySrf')
        rs.Command('_Enter')

        Wireframe = rs.LastCreatedObjects(True)
        for id in Wireframe:
            rs.ObjectLayer(id, layer)

    rs.CurrentLayer('Default')
    # rs.SurfaceIsocurveDensity(PolySrf, 0)


def Make2D():
    '''
    [See](https://github.com/localcode/rhinopythonscripts/blob/master/Make2D.py)
    [`Make2D`](http://docs.mcneel.com/rhino/5/help/en-us/commands/make2d.htm)

    `rs.Command('Make2D')` produces popup. Possible to interact with combobox programatically

    From `Perspective` position camera and ensure only:
        * PolySrf
        * Wireframe
        * Intersections
    Or:
        * PolySrf
        * Border
        * Edges
        * Intersections
    Layers are visible


    `Make2D` options:
        Drawing layout
            * Current View

        Options
            * Show tangent edges
            * show hidden lines
            * show viewport rectangle
            * maintain sourc layers

        layers for Make2D objects
            * visible lines
            * visible tangents
            * visible clipping plane
            * hidden lines
            * hidden tangents
            * hidden clipping planes
            * annotations

    Export:
        * Swith to Top View
        * Hide all layers but 2D::visible
        * `SelCrv`
        * `File > Export Selected`.
        * Use *.ai. Experiment with scale.

    '''
    return

    # sticky['layerCount'] = 1
    # '::'.join(['2D', sticky['layerCount'] += 1, ])

    # rs.Command(
    #     "Make2D DrawingLayout=CurrentView " +
    #     "ShowTangentEdges=Yes " +
    #     "CreateHiddenLines=Yes " +
    #     "MaintainSourceLayers=Yes Enter " +
    #     "-Invert Hide SetView World Top ZE SelNone",
    #     False
    # )

    # switchLayers("viewportFramework - Hidden", "viewportFramework - Visible")

    # zoomToLayer("viewportFramework - Visible")
    #

    # app.RunScript("SelAll -Export "+export
    #         +" PreserveUnits=No "
    #         +"ViewportBoundary=Yes Enter", False)
