import System.Guid
import System.Drawing
from scriptcontext import doc
import rhinoscriptsyntax as rs
from Rhino.Geometry import Vector3d, Plane, Point3d, Brep


layers = [
    'PolySrf',              # `Join` Patches
    'Intersect::Curves',    # Perform before `Join`. `Intersection` Curves
    'Intersect::Points',
    'Border::All',          # `Join` + `DupBorder`
    'Border::Outer',        # Perform before `Join`. `SelAll` Patches + `DupBorder`
    'Silhouette',           # `Join` + `Silhouette`. Weird artifacts across surface
    'Wireframe',            # Set `SurfaceIsocurveDensity` then `Join` + `ExtractWireframe`.
    'RenderMesh',           # Set `SurfaceIsocurveDensity` then `Join` + `ExtractRenderMesh`.
    '2D'                    # Project to 2D plane
]


def Build():
    Layers()
    Patches()
    Intersect()
    Border()
    # Silhouette()
    Wireframe()

    rs.EnableRedraw(True)
    doc.Views.Redraw()


def Layers():
    for layer in layers:
        if not rs.IsLayer(layer):
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
    rs.CurrentLayer('Default')
    rs.ObjectsByType(rs.filter.surface, True)
    rs.Command('_Intersect')

    for id in rs.ObjectsByType(rs.filter.point):
        rs.ObjectLayer(id, 'Intersect::Points')

    for id in rs.ObjectsByType(rs.filter.curve):
        rs.ObjectLayer(id, 'Intersect::Curves')

    rs.LayerLocked('Intersect::Points', True)
    rs.LayerLocked('Intersect::Curves', True)
    rs.LayerLocked('Intersect', True)


def Border():
    rs.CurrentLayer('Default')
    for Srf in rs.ObjectsByType(rs.filter.surface, True):
        for id in rs.DuplicateSurfaceBorder(Srf, 1):
            rs.ObjectLayer(id, 'Border::All')

    rs.CurrentLayer('PolySrf')
    for PolySrf in rs.ObjectsByType(rs.filter.polysurface, True):
        for id in rs.DuplicateSurfaceBorder(PolySrf, 1):
            rs.ObjectLayer(id, 'Border::Outer')

    rs.LayerLocked('Border::All', True)
    rs.LayerLocked('Border::Outer', True)
    rs.LayerLocked('Border', True)


def Silhouette():
    rs.CurrentLayer('PolySrf')
    rs.Command('_Silhouette')
    for id in rs.ObjectsByType(rs.filter.curve, True):
        rs.ObjectLayer(id, 'Silhouette')
    rs.LayerLocked('Silhouette', True)


def Wireframe():
    for i in range(1, 5, 1):
        rs.CurrentLayer('PolySrf')

        layer = 'Wireframe::' + str(i)
        if not rs.IsLayer(layer):
            rs.AddLayer(layer, System.Drawing.Color.Black)
        rs.LayerVisible(layer, False)

        for PolySrf in doc.Objects.FindByLayer('PolySrf'):
            obj = rs.coercerhinoobject(PolySrf, True, True)
            obj.Attributes.WireDensity = i
            obj.CommitChanges()

        rs.CurrentLayer('PolySrf')

        rs.ObjectsByType(rs.filter.polysurface, True)
        rs.Command(
            '_ExtractWireframe'
            + ' OutputLayer=Input'
            + ' GroupOutput=Yes'
            + ' _Enter'
        )

        for id in rs.LastCreatedObjects(True):
            rs.ObjectLayer(id, layer)

        rs.LayerLocked(layer, True)
    rs.LayerLocked('Wireframe', True)


def Make2D():
    '''
    [See](https://github.com/localcode/rhinopythonscripts/blob/master/Make2D.py)
    [`Make2D`](http://docs.mcneel.com/rhino/5/help/en-us/commands/make2d.htm)

    `rs.Command('Make2D')` produces popup. Possible to interact with combobox programatically

    From `Perspective` position camera and ensure only:
        * PolySrf
        * Wireframe
        * Intersect
    Or:
        * PolySrf
        * Border
        * Edges
        * Intersect
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
