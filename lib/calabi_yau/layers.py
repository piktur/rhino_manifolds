import System.Guid
import System.Drawing
from scriptcontext import doc
import rhinoscriptsyntax as rs
from Rhino.Geometry import Vector3d, Plane, Point3d, Brep, Intersect, Curve
from Rhino.Collections import Point3dList, CurveList


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
    SetCamera()

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


def BoundingBox():
    PolySrf = rs.ObjectsByLayer('PolySrf')[0]
    box = rs.BoundingBox(PolySrf)

    for i, p in enumerate(box):
        doc.Objects.AddTextDot(str(i), p)

    return box


def SetCamera():
    box = BoundingBox()
    line = rs.AddLine(box[4], box[2])
    rs.MoveObject(line, box[4] - box[2])
    line = rs.coerceline(line)

    rs.AddNamedView('Base', 'Perspective')
    rs.ViewProjection('Base', 1)
    rs.ViewCamera('Base', line.From)
    rs.ViewTarget('Base', line.To)

    # index = scriptcontext.doc.NamedViews.FindByName('Base')
    # viewinfo = doc.NamedViews[index]

    # view = doc.Views.ActiveView
    # if view.MainViewport.PushViewInfo(viewinfo, False):
    #     view.Redraw()

    # view.ActiveViewport.ChangeToParallelProjection(True)


def Split():
    surfaces = []
    tolerance = doc.ModelAbsoluteTolerance

    for id in rs.ObjectsByLayer('Default'):
        surfaces.append((id, rs.coercebrep(id, True)))

    for obj1 in surfaces:
        brep1_id, brep1 = obj1
        for obj2 in surfaces:
            brep2_id, brep2 = obj2

            if brep1_id != brep2_id:
                rc = Intersect.Intersection.BrepBrep(brep1, brep2, tolerance)
                if rc:
                    breps = brep1.Split(brep2, tolerance)

                    if len(breps) > 0:
                        rhobj = rs.coercerhinoobject(brep1_id, True)
                        if rhobj:
                            attr = rhobj.Attributes if scriptcontext.id == 1 else None
                            rc = []
                            for i in range(len(breps)):
                                if i == 0:
                                    doc.Objects.Replace(rhobj.Id, breps[i])
                                    rc.append(rhobj.Id)
                                else:
                                    rc.append(doc.Objects.AddBrep(breps[i], attr))
                        else:
                            rc = [doc.Objects.AddBrep(brep) for brep in breps]

    doc.Views.Redraw()


def Intersect():
    '''
    # Equivalent to `rs.Command('Intersect')`
        surfaces = []
        for obj in rs.ObjectsByLayer('Default'):
        surfaces.append(rs.coercebrep(obj))

        for a in surfaces:
            for b in surfaces:
                if a != b:
                    rs.IntersectBreps(a, b, doc.ModelAbsoluteTolerance)
    '''
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

    # import Rhino
    # import System
    # from Rhino.Geometry import *
    # from scriptcontext import doc
    # import rhinoscriptsyntax as rs
    # import Rhino.RhinoApp as app
    # from InfraPy import *
    #
    # import os
    # import sys
    #
    #
    # def addRhinoLayer(layerName, layerColor=System.Drawing.Color.Black):
    #     """Creates a Layer in Rhino using a name and optional color. Returns the index of the created layer. If the layer
    #     already exists, no new layer is created."""
    #     docLyrs = doc.Layers
    #     layerIndex = docLyrs.Find(layerName, True)
    #     if layerIndex == -1:
    #         layerIndex = docLyrs.Add(layerName,layerColor)
    #     return layerIndex
    #
    # def layerAttributes(layerName, layerColor=System.Drawing.Color.Black):
    #     """Returns a Rhino ObjectAttributes object for a rhino layer with an optional color."""
    #     att = Rhino.DocObjects.ObjectAttributes()
    #     att.LayerIndex = addRhinoLayer(layerName, layerColor)
    #     return att
    #
    # def addBBoxOutlines():
    #     """Adds a wireframe of the bounding box to use for zooming"""
    #     bAtt = layerAttributes("bBoxWires", System.Drawing.Color.BlanchedAlmond)
    #     bBox = doc.Objects.FindByLayer("boundingBox")[0].Geometry
    #     bCurves = bBox.DuplicateEdgeCurves()
    #     for curve in bCurves:
    #         doc.Objects.AddCurve(curve, bAtt)
    #     return True
    #
    # def switchLayers(fromLayer, toLayer):
    #     """gets the objects on fromLayer and moves them to toLayer."""
    #     objs = doc.Objects.FindByLayer(fromLayer)
    #     lIndex = doc.Layers.Find(toLayer, True)
    #     for obj in objs:
    #         obj.Attributes.LayerIndex = lIndex
    #         obj.CommitChanges()
    #
    #
    # def deleteEverything():
    #     """Deletes everything in the current Rhino document. Returns nothing."""
    #     guidList = []
    #     objType = Rhino.DocObjects.ObjectType.AnyObject
    #     objTable = doc.Objects
    #     objs = objTable.GetObjectList(objType)
    #     for obj in objs:
    #         guidList.append(obj.Id)
    #     for guid in guidList:
    #         objTable.Delete(guid, True)
    #
    # def viewportSetup(lensLength=900.0, size=800):
    #     app.RunScript("4View -NewFloatingViewport Projection=Perspective", False)
    #     cameraLine = doc.Objects.FindByLayer("viewLine")[0].Geometry
    #     targetPoint = cameraLine.PointAtEnd
    #     cameraPoint = cameraLine.PointAtStart
    #     view = doc.Views.ActiveView.ActiveViewport
    #     view.SetCameraLocations(targetPoint, cameraPoint)
    #     view.Camera35mmLensLength = lensLength
    #     app.RunScript("-ViewportProperties Size "+str(size)+" "+str(size)+" Enter", False)
    #     bBox = doc.Objects.FindByLayer("boundingBox")[0].Geometry.GetBoundingBox(True)
    #     view.ZoomBoundingBox(bBox)
    #
    # def viewportRectangle():
    #     m = doc.Views.ActiveView.ActiveViewport.GetNearRect()
    #     rect = Rhino.Geometry.Curve.CreateControlPointCurve(m, 1)
    #     att = layerAttributes("viewportRectangle", System.Drawing.Color.Cyan )
    #     att.Mode = Rhino.DocObjects.ObjectMode.Normal
    #     id = doc.Objects.AddCurve(rect, att)
    #     doc.Objects.Find(id).CommitChanges()
    #
    # def viewportFramework():
    #     view = doc.Views.ActiveView.ActiveViewport
    #     near = view.GetNearRect()
    #     far = view.GetFarRect()
    #     att = layerAttributes("viewportFramework", System.Drawing.Color.Cyan )
    #     pairs = crossMatch(near, far)
    #     for pair in pairs:
    #         cv = Rhino.Geometry.Curve.CreateControlPointCurve(pair, 1)
    #         id = doc.Objects.AddCurve( cv, att )
    #         doc.Objects.Find(id).CommitChanges()
    #
    #
    #
    # def crossMatch(list1, list2):
    #     outList = []
    #     for i in list1:
    #         for j in list2:
    #             pair = ( i, j )
    #             outList.append(pair)
    #     return outList
    #
    #
    # def configureLayers(layerConfigTable):
    #     for layerSettings in layerConfigTable:
    #         rs.LayerVisible(layerSettings[0], layerSettings[1])
    #         if layerSettings[2] != None:
    #             rs.LayerColor(layerSettings[0], layerSettings[2])
    #
    # def restoreLayers():
    #     for i in range(doc.Layers.ActiveCount):
    #         doc.Layers.SetCurrentLayerIndex(i, True)
    #         name = doc.Layers.CurrentLayer.Name
    #         rs.LayerVisible(name, True)
    #     doc.Layers.SetCurrentLayerIndex(0, True)
    #
    # def deleteLayer(layer_index):
    #     settings = Rhino.DocObjects.ObjectEnumeratorSettings()
    #     settings.LayerIndexFilter = layer_index
    #     objs = doc.Objects.FindByFilter(settings)
    #     ids = []
    #     for obj in objs:
    #         obj.Attributes.Visible = True
    #         obj.CommitChanges()
    #         ids.append(obj.Id)
    #     for id in ids:
    #         doc.Objects.Delete(id, True)
    #     doc.Layers.Delete(layer_index, True)
    #
    # def fixCurves():
    #     app.RunScript("-SelNone", False)
    #     for i in range(doc.Layers.ActiveCount):
    #         if doc.Layers[i].IsVisible == True:
    #             doc.Layers.SetCurrentLayerIndex(i, True)
    #             name = doc.Layers.CurrentLayer.Name
    #             objs = doc.Objects.FindByLayer(name)
    #             for obj in objs:
    #                 obj.Select(True)
    #             app.RunScript("-Join Enter", False)
    #             app.RunScript("-SelNone", False)
    #
    #
    #
    # def zoomToLayer(layerName):
    #     """
    #     selects the first item in the named layer and zooms to that object
    #     """
    #     objs = doc.Objects.FindByLayer(layerName)
    #     ptList = []
    #     for obj in objs:
    #         ptList.append(obj.Geometry.PointAtStart)
    #         ptList.append(obj.Geometry.PointAtEnd)
    #     bbx = Rhino.Geometry.BoundingBox(ptList)
    #     doc.Views.ActiveView.ActiveViewport.ZoomBoundingBox(bbx)
    #
    #
    # if __name__=="__main__":
    #
    #     layerConfigurationTable = [
    #             ("boundingBox", False, None),
    #             ("viewLine", False, None),
    #             ("BuildingVolumes", False, None)
    #             ]
    #     make2DLayerTable = [
    #             ("TerrainWireframe - Hidden", False, None),
    #             ("BuildingWireframes - Hidden", False, None),
    #             ("BuildingVolumes", False, None),
    #             ("LabelLines - Hidden", True, None)
    #             ]
    #
    #     files = listFiles("/Users/daniel/Documents/Design", True, ".3dm")
    #     files = files[680:]
    #     n = editFilePrefix("/Users/daniel/Documents/Design","C:\\LocalCodeFullBatch\\AiAxo\\AiAxo",files)
    #     exports = editFileExt(".3dm", ".ai", n)
    #     opt = Rhino.FileIO.FileReadOptions()
    #     opt.ImportMode=True
    #
    #     for i in range(len(files)): # slice the files list here to limit the size of the batch (files[:10])
    #         file = files[i]
    #         export = exports[i]
    #
    #         # restoreLayers()
    #         restoreLayers()
    #         app.RunScript("Show ", False)
    #
    #         # clear the current file
    #         deleteEverything()
    #         app.RunScript("-CloseViewport ", False)
    #
    #         # import the new file
    #         doc.ReadFile(file, opt)
    #
    #         # set up the viewport
    #         viewportSetup(275, 800)
    #
    #         viewportFramework()
    #
    #         addBBoxOutlines()
    #
    #
    #         # set up the layers
    #         configureLayers(layerConfigurationTable)
    #
    #         # rs.Command(
    #         #     "Make2D DrawingLayout=CurrentView " +
    #         #     "ShowTangentEdges=Yes " +
    #         #     "CreateHiddenLines=Yes " +
    #         #     "MaintainSourceLayers=Yes Enter " +
    #         #     "-Invert Hide SetView World Top ZE SelNone",
    #         #     False
    #         # )
    #
    #         ## Do a make 2D
    #         app.RunScript("SelAll -Make2D DrawingLayout=CurrentView "
    #                 +"ShowTangentEdges=Yes "
    #                 +"CreateHiddenLines=Yes "
    #                 +"MaintainSourceLayers=Yes Enter "
    #                 +"-Invert Hide SetView World Top ZE SelNone",
    #                 False)
    #
    #         switchLayers("viewportFramework - Hidden", "viewportFramework - Visible")
    #
    #         zoomToLayer("viewportFramework - Visible")
    #
    #
    #         app.RunScript("SelAll -Export "+export
    #                 +" PreserveUnits=No "
    #                 +"ViewportBoundary=Yes Enter", False)
