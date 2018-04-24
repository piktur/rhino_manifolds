import os
import errno
import sys
import json
import string
import System
import System.Guid
from System.Drawing import Color
from System.IO import Path, File, FileInfo, FileAttributes
import System.Collections.Generic as SCG
from scriptcontext import doc, sticky
import rhinoscriptsyntax as rs
from Rhino.FileIO import FileWriteOptions, FileReadOptions
from Rhino.Geometry import Point3d, Brep, BrepFace, Surface, NurbsSurface, Interval, Curve, Intersect
from Rhino.Collections import Point3dList, CurveList
from Rhino.RhinoApp import RunScript


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def fname(format='3dm', path='', *fname):
    basename = '_'.join(map(lambda e: str(e), fname)) + '.' + format
    mkdir_p(path)
    return os.path.join(path, basename)


def coercecurvelist(obj):
    if not isinstance(obj, CurveList):
        obj = CurveList(obj)

    return obj


def rendered(obj):
    '''
    Confirm `obj` present in document Guid
    '''
    if obj == System.Guid.Empty:
        raise Exception('RenderError')

    return True


def render(geometry, layer=None):
    if isinstance(geometry, Point3d):
        id = doc.Objects.AddPoint(geometry)
    else:
        id = doc.Objects.Add(geometry)
    rendered(id)

    if layer:
        str = AddLayer(layer)
        rs.ObjectLayer(id, str)

    return id


def layer(*args):
    return '::'.join([str(e) for e in args])


def __path__(nodes, sep=';'):
    return sep.join([str(n) for n in nodes])


def chunk(arr, size):
    '''
    Yield successive chunks of `size` from `list`.
    '''
    for i in range(0, len(arr), size):
        yield arr[i:i + size]


def AddLayer(str, colour=None):
    if not rs.IsLayer(str):
        rs.AddLayer(str, colour)

    return str


def PurgeLayer(layer):
    '''
    Delete a layer, sublayers and geometry

    Parameters:
        layer : str
    '''
    if not rs.IsLayer(layer):
        return

    layer = doc.Layers.FindByFullPath(layer, True)
    children = doc.Layers[layer].GetChildren()

    if children:
        for child in children:
            PurgeLayer(child.FullPath)

    doc.Layers.Purge(layer, True)
    doc.Views.Redraw()


def PurgeAll():
    '''
    Delete all objects within document
    '''
    rs.CurrentLayer('Default')

    for layer in rs.LayerNames():
        if rs.IsLayer(layer) and layer != 'Default':
            rs.PurgeLayer(layer)

    objs = []
    objTable = doc.Objects
    for obj in objTable.GetObjectList(Rhino.DocObjects.ObjectType.AnyObject):
        objs.append(obj.Id)
    for guid in objs:
        objTable.Delete(guid, True)


def Visible(layer, visible=True):
    '''
    Set Layer visibility

    Parameters:
        layer : str
        visible : bool
    '''
    def toggle(layer):
        id = doc.Layers.FindByFullPath(layer, True)
        layer = doc.Layers[id]
        layer.IsVisible = visible
        layer.CommitChanges()

    if visible:  # Step through path
        path = string.split(layer, '::')
        for i in range(len(path)):
            toggle('::'.join(path[0:i + 1]))
    else:
        toggle(layer)


def Transfer(origin, destination):
    '''
    Transfer object to layer. Use in place of `rs.RenameLayer()`

    Parameters:
        origin : str
        destination : str
    '''
    # Ensure destination layer exists
    if not rs.IsLayer(destination):
        rs.AddLayer(destination)

    if rs.IsLayer(origin):
        rs.LayerVisible(origin, True, True)

        for id in rs.ObjectsByLayer(origin, True):
            rs.ObjectLayer(id, destination)

    doc.Views.Redraw()


def Export(queue, cb=None, dir='~/Documents/CY'):
    '''
    [See](https://bitbucket.org/kunst_dev/snippets/issues/11/export-2d)
    Parameters:
        queue : dict
        cb: function
        dir : string
    Example:
        dir = rs.GetString('Destination')
        Export(CalabiYau.Batch(dir), CalabiYau.Make2D, dir)

    TODO
        def CreateWireframePreviewImage()
            preview = fname('jpg', path, f)
            view = doc.Views.Find('Top', False)
            previewSize = System.Drawing.Size(100, 100)  # view.ClientRectangle.Size
            view.CreateWireframePreviewImage(preview, previewSize, True, False)
    '''
    def WriteFile(filePath, version=5, geomOnly=False, selectedOnly=False):
        '''
        Export a file.
        [See](https://github.com/localcode/rhinopythonscripts/blob/34c5314/FileTools.py)
        '''
        opt = FileWriteOptions()
        opt.FileVersion = version
        opt.WriteGeometryOnly = geomOnly
        opt.WriteSelectedObjectsOnly = selectedOnly

        return doc.WriteFile(filePath, opt)

    for (path, obj) in queue.iteritems():
        obj.Build()
        obj.AddLayers(obj.Layers)
        obj.Render()
        obj.Finalize()

        doc.Views.Redraw()

        if callable(cb):
            cb()

        WriteFile(path)
        PurgeAll()


def ExportNamedViews():
    '''
    Extract view coordinates and write to JSON

    Example:
        * Open original .3dm file
        * RunPythonScript `ExportNamedViews()`
        * Create a New .3dm file
        * RunPythonScript `ImportNamedViews()`
    '''
    log = open('./views.json', 'a')
    fname = rs.DocumentPath() + rs.DocumentName()
    data = {}
    data[fname] = {}

    for view in rs.NamedViews():
        rs.RestoreNamedView(view)
        data[fname][view] = (
            list(rs.ViewCamera()),
            list(rs.ViewTarget())
        )

    log.write(json.dumps(data, indent=2) + '\n')
    log.close()

    return data


def ImportNamedViews():
    '''
    Read JSON and add view coordinates to document
    '''
    with open('./views.json') as log:
        data = json.load(log)

    for (fname, views) in data.iteritems():
        for (view, coords) in views.iteritems():
            camera, target = coords
            if view != 'Base':
                rs.ViewCameraTarget(camera=camera, target=target)
                view = rs.AddNamedView(name=view)


def Palette():
    '''
    Returns 2D list of colours 10 * 4
    '''
    arr = []
    for i in range(25, 255, 51):  # 255 / 51 == 5
        arr.append((
            Color.FromArgb(i, 0, i),  # Red-Blue
            Color.FromArgb(0, 0, i),  # Blue
            Color.FromArgb(0, i, i),  # Green-Blue
            Color.FromArgb(0, i, 0),  # Green
            Color.FromArgb(i, i, 0),  # Green-Red
            Color.FromArgb(i, 0, 0)   # Red
        ))

    return arr


class IsoGrid():
    __slots__ = [
        'TrimAware',
        'isSurface', 'isBrepFace',
        'Surface',
        'Mesh',
        'Parameters', 'Points', 'Normals', 'inc',
        'U', 'V',
        'CurvesU', 'CurvesV',
        'SubSurfaces',
        'Phase',
        '__conf__'
    ]

    def __init__(self, srf, U, V, TrimAware=True, Phase=()):
        self.TrimAware = TrimAware
        self.isSurface = isinstance(srf, Surface)
        self.isBrepFace = isinstance(srf, BrepFace)
        self.Surface = srf if self.isBrepFace else Brep.TryConvertBrep(srf).Faces[0]
        self.Parameters = []
        self.Points = Point3dList()
        self.Normals = []
        self.inc = []
        self.U = U
        self.V = V
        self.Curves = {CurveList() for char in 'UV'}
        # self.SubSurfaces = {Phase[0]: {Phase[1]: {}}}
        self.SubSurfaces = []
        self.Phase = Phase

        # subSurfaces[patch.Phase] = {}
        # subSurfaces[patch.Phase][key] = {}

        quad = range(4)
        self.__conf__ = {
            'quad': quad,
            'combinations': zip(quad, (1, 2, 3, 0)),
            'tolerance': doc.ModelAbsoluteTolerance
        }

    def Build(self, geometry=1, experimental=False, euqalizeSpanLength=False):
        if experimental:
            self.QuadGrid()
        else:
            if euqalizeSpanLength:
                self.UVGridEqualized()
            else:
                self.UVGrid()

            if geometry == 0:
                self.BuildMesh(layer)
            elif geometry == 1:
                self.BuildSubSurfaces(layer)

    def UVGrid(self):
        countU = 0

        while countU <= self.U:
            intervalU = self.Surface.Domain(0)
            u = intervalU.ParameterAt(countU / self.U)

            countV = 0
            while countV <= self.V:
                intervalV = self.Surface.Domain(1)
                v = intervalV.ParameterAt(countV / self.V)

                self.Parameters.append([u, v])

                point = self.Surface.PointAt(u, v)
                self.Points.Add(point)

                normal = self.Surface.NormalAt(u, v)
                self.Normals.append(normal)

                if self.isBrepFace:
                    self.inc.append(self.Surface.IsPointOnFace(u, v))
                else:
                    self.inc.append(True)

                countV += 1
            countU += 1

    def UVGridEqualized(self):
        isoCurvesU = self.ExtractIsoCurves(2.0, 1, 1, 0)
        isoCurvesV = self.ExtractIsoCurves(2.0, 0, 0, 1)

        countU = 0
        while countU <= self.U:
            curve = self.FitEqualizedIsoCurveUV(self.Surface, isoCurvesU, countU / self.U)
            if curve:
                self.Curves['U'].Add(curve)
                countV = 0
                while countV <= self.V:
                    result, parameter = curve.NormalizedLengthParameter(countV / self.V)
                    if result:
                        point = curve.PointAt(parameter)

                        result, u, v = self.Surface.ClosestPoint(point)
                        if result:
                            self.Parameters.append([u, v])

                            point = self.Surface.PointAt(u, v)
                            self.Points.Add(point)

                            normal = self.Surface.NormalAt(u, v)
                            self.Normals.append(normal)

                            if self.isBrepFace:
                                self.inc.append(self.Surface.IsPointOnFace(u, v))
                            else:
                                self.inc.append(True)
                    countV += 1
            countU += 1

        countV = 0
        while countV <= V:
            curve = self.FitEqualizedIsoCurve(isoCurvesV, countV / V)
            if curve:
                self.Curves['V'].Add(curve)

            countV += 1

    def BuildMesh(self, layer):
        maxU = self.U - 1  # zero offset
        count = self.Points.Count - 1
        countU = 0
        i = 0
        self.Mesh = Mesh()

        while i <= count:
            self.Mesh.Vertices.Add(points[i])
            self.Mesh.Normals.Add(normals[i])
            i += 1

        while countU <= maxU:
            maxV = self.V - 1  # zero offset
            countV = 0

            while countV <= maxV:
                # Here we build our GRID
                i0 = (countU * (self.V + 1) + countV)
                i1 = (i0 + self.V + 1)
                i2 = (i1 + 1)
                i3 = (i0 + 1)

                if self.TrimAware:
                    if self.inc[i0] or self.inc[i1] or (self.inc[i2] or self.inc[i3]):
                        self.Mesh.Faces.AddFace(i0, i1, i2, i3)
                elif self.inc[i0] and self.inc[i1] and (self.inc[i2] and self.inc[i3]):
                    self.Mesh.Faces.AddFace(i0, i1, i2, i3)

                countV += 1
            countU += 1

        self.Mesh.Vertices.CullUnused()

        return self.Mesh

    def BuildSubSurfaces(self, layer):
        tolerance = self.__conf__['tolerance']
        maxU = self.U - 1  # zero offset
        count = self.Points.Count - 1
        countU = 0
        i = 0

        while countU <= maxU:
            # self.SubSurfaces[countU] = {}

            maxV = self.V - 1  # zero offset
            countV = 0

            while countV <= maxV:
                edges = CurveList()

                i0 = countU * (self.V + 1) + countV
                i1 = i0 + self.V + 1
                i2 = i1 + 1
                i3 = i0 + 1

                c0, c1, c2, c3 = [
                    self.Parameters[eval('i' + str(n))] for n in self.__conf__['quad']
                ]
                if self.TrimAware:
                    if self.inc[i0] or self.inc[i1] or (self.inc[i2] or self.inc[i3]):
                        for t in self.__conf__['combinations']:
                            vertex = rs.coerce2dpointlist([eval('c' + str(n)) for n in t])
                            curve = self.Surface.InterpolatedCurveOnSurfaceUV(vertex, tolerance)
                            if curve:
                                edges.Add(curve)
                    elif self.inc[i0] and self.inc[i1] and (self.inc[i2] and self.inc[i3]):
                        for t in self.__conf__['combinations']:
                            vertex = rs.coerce2dpointlist([eval('c' + str(n)) for n in t])
                            curve = self.Surface.InterpolatedCurveOnSurfaceUV(vertex, tolerance)
                            if curve:
                                edges.Add(curve)

                subSrf, err = NurbsSurface.CreateNetworkSurface(
                    edges,
                    3,
                    0.1,
                    0.1,
                    1.0
                )

                if subSrf:
                    self.SubSurfaces.append(subSrf)
                # self.SubSurfaces[countU][countV] = subSrf
                # __path__(self.Phase + (countU, countV))

                countV += 1
            countU += 1

        return self.SubSurfaces

    def QuadGrid(self):
        '''
        Lunchbox | Creates a quad corner point grid on a surface.
        Parameters:
            srf : Rhino.Geometry.NurbsSurface
            U : int
                range(0,10)
            U : int
                range(0,10)
        Returns:
            quad : tuple<Rhino.Geometry.Point3d>
            midPoint : Rhino.Geometry.Point3d
                The midpoint of the quad
            normals : Rhino.Geometry.Vector3d
                Normal vector at midpoint
        '''
        tolerance = self.__conf__['tolerance']

        result, maxU, maxV = self.Surface.GetSurfaceSize()
        self.Surface.SetDomain(0, Interval(0, 1))
        self.Surface.SetDomain(1, Interval(0, 1))

        midPoints = Point3dList()
        normals = []

        p0 = Point3dList()
        p1 = Point3dList()
        p2 = Point3dList()
        p3 = Point3dList()

        u = 1.0 / float(self.U)
        v = 1.0 / float(self.V)

        for i in range(self.U):
            # self.SubSurfaces[i] = {}

            for j in range(self.V):
                midPoint = self.Surface.PointAt((i * u) + (0.5 * u), (j * v) + (0.5 * v))
                vector = self.Surface.NormalAt((i * u) + (0.5 * u), (j * v) + (0.5 * v))

                uv0 = [float(i * u), float(j * v)]
                uv1 = [float(i + 1.0) * u, float(j * v)]
                uv2 = [float(i + 1.0) * u, float(j + 1.0) * v]
                uv3 = [float(i * u), float(j + 1.0) * v]

                edges = CurveList()
                if False:  # Through points
                    c0 = self.Surface.PointAt(*uv0)
                    c1 = self.Surface.PointAt(*uv1)
                    c2 = self.Surface.PointAt(*uv2)
                    c3 = self.Surface.PointAt(*uv3)

                    for t in self.__conf__['combinations']:
                        arr = [eval('c' + str(n)) for n in t]
                        curve = self.Surface.InterpolatedCurveOnSurface(arr, tolerance)
                        edges.Add(curve)
                else:  # Through parameter space
                    for t in self.__conf__['combinations']:
                        arr = [eval('uv' + str(n)) for n in t]
                        arr = rs.coerce2dpointlist(arr)
                        curve = self.Surface.InterpolatedCurveOnSurfaceUV(arr, tolerance)
                        edges.Add(curve)

                subSrf, err = NurbsSurface.CreateNetworkSurface(
                    edges,
                    1,
                    0.1,
                    0.1,
                    1.0
                )

                if subSrf:
                    self.SubSurfaces.append(subSrf)
                # self.SubSurfaces[i][j] = subSrf
                # __path__(self.Phase + (i, j))

                midPoints.Add(midPoint)
                normals.append(vector)
                # p0.Add(c0)
                # p1.Add(c1)
                # p2.Add(c2)
                # p3.Add(c3)

        return midPoints, p0, p1, p2, p3, normals

    def ExtractIsoCurves(self, n, domain, span, isocurve):
        interval = self.Surface.Domain(domain)
        min = interval.Min
        max = interval.Max

        curves = CurveList()
        div = n * self.Surface.SpanCount(span)
        count = 0

        while count <= div:
            t = (min + (count / div)) * (max - min)
            curves.Add(self.Surface.IsoCurve(isocurve, t))
            count += 1

        return curves

    @staticmethod
    def FitEqualizedIsoCurve(srf, curves, div):
        points = []
        count = curves.Count - 1  # zero offset
        i = 0

        while i <= count:
            result, point, u, v = IsoGrid.PointAtRatio(srf, curves[i], div)
            if result:
                points.append(point)
            i += 1

        return srf.InterpolatedCurveOnSurface(points, tolerance)

    @staticmethod
    def FitEqualizedIsoCurveUV(srf, curves, div):
        points = []
        count = curves.Count - 1  # zero offset
        i = 0

        while i <= count:
            result, point, u, v = IsoGrid.PointAtRatio(srf, curves[i], div)
            if result:
                points.append([u, v])
            i += 1

        # points = rs.coerce2dpointlist(points[0::count])
        points = rs.coerce2dpointlist(points)

        return srf.InterpolatedCurveOnSurfaceUV(points, tolerance)

    @staticmethod
    def PointAtRatio(srf, curve, div):
        result, parameter = curve.NormalizedLengthParameter(div)
        if result:
            point = curve.PointAt(parameter)
            result, u, v = srf.ClosestPoint(point)
            if result:
                return True, srf.PointAt(u, v), u, v


def RemoveOverlappingCurves(setA, setB, tolerance=0.1):  # doc.ModelAbsoluteTolerance
    '''
    Compare low/high precision Curve sets and remove low precision Cuve when overlapping.

    Parameters:
        setA : list<Rhino.DocObjects.RhinoObject>
            Low precision Curve identifiers
        setB : list<Rhino.DocObjects.RhinoObject>
            High precision Curve identifiers
        tolerance : float
    '''
    for i2, obj1 in enumerate(setA):
        c1 = rs.coercecurve(obj1)

        if c1:
            for i2, obj2 in enumerate(setB):
                c2 = rs.coercecurve(obj2)

                if c2:
                    result = Intersect.Intersection.CurveCurve(c1, c2, tolerance, tolerance)

                    if result:
                        for event in result:
                            if event.IsOverlap:
                                deviation = Curve.GetDistancesBetweenCurves(c1, c2, tolerance)

                                # minA = deviation[5]
                                maxaA = deviation[2]

                                # maxB = deviation[3]
                                # minB = deviation[6]

                                # minDeviation = deviation[4]
                                maxDeviation = deviation[1]

                                if maxDeviation < tolerance:
                                    l1 = c1.Length if hasattr(c1, 'Length') else c1.GetLength()
                                    l2 = c2.Length if hasattr(c2, 'Length') else c2.GetLength()

                                    # Keep longer
                                    if l1 > l2:
                                        rs.DeleteObject(obj2)
                                    else:
                                        rs.DeleteObject(obj1)


def Make2d():
    '''
    Rhinoceros Mac v5.4 WIP, 2D output improves when run with a smaller subset of objects.
    This macro generates 2D curves in three stages:
        1. Surface and intersections
        2. Surface U IsoCurves
        2. Surface V IsoCurves
    Due to form complexity, rounding issues/floating point mathematics,
    manual correction may be required.

    [1](https://gist.github.com/bengolder/3959792)
    [2](http://archiologics.com/2011-10-20-15-32-52/rhino-scripts/animation-tools/81-rvb-batch-render-make2d)
    [3](https://github.com/localcode/rhinopythonscripts/blob/master/Make2D.py)
    [4](http://docs.mcneel.com/rhino/5/help/en-us/commands/make2d.htm)
    '''
    def run():
        RunScript(
            '-Make2D  DrawingLayout=CurrentView '
            + 'ShowTangentEdges=Yes '
            + 'CreateHiddenLines=No '
            + 'MaintainSourceLayers=Yes '
            + 'Enter ',
            True
        )

    baseLayers = [
        layer('PolySurfaces', 1),
        layer('Intersect', 'Curves')
    ]

    rs.CurrentLayer('Default')

    # Hide all Layers
    for l in rs.LayerNames():
        if l != 'Default':
            Visible(l, False)

    for view in rs.NamedViews():
        if view != 'Base':
            rs.RestoreNamedView(view)

            # 1. Generate Outlines
            # Generate 2D curves with relaxed tolerance(s) (decrease accuracy)
            # Curves are generated twice, once per tolerance,
            # to increase coverage and minimise fragmentation.
            for i, tolerance in enumerate((0.1, 0.001)):
                rs.UnitAbsoluteTolerance(tolerance, True)

                rs.UnselectAllObjects()

                # Select objects
                for l in baseLayers:
                    if rs.IsLayer(l):
                        rs.LayerVisible(l, True, True)
                        rs.ObjectsByLayer(l, True)

                run()

                # Transfer 2D curves to View layer
                for l in baseLayers:
                    for child in ('lines', 'tangents'):
                        a = layer('Make2D', 'visible', child, l)
                        b = layer(view, 'visible', child, str(i), l)

                        Transfer(a, b)
                        Visible(view, False)

                PurgeLayer('Make2D')

            # 2. Generate IsoCurves
            # Decrease tolerance (increase accuracy)
            rs.UnitAbsoluteTolerance(0.0000000001, True)

            # Run Make2D once per curve direction
            for dimension in 'UV':
                isoCurves = layer('Curves', 1, 0, dimension)
                layers = list(baseLayers)  # copy
                layers.append(isoCurves)

                rs.UnselectAllObjects()

                # Select objects
                for l in layers:
                    if rs.IsLayer(l):
                        rs.LayerVisible(l, True, True)
                        rs.ObjectsByLayer(l, True)

                run()

                a = layer('Make2D', 'visible', 'lines', isoCurves)
                b = layer(view, 'visible', 'lines', isoCurves)

                Transfer(a, b)

                Visible(view, False)
                Visible(isoCurves, False)
                PurgeLayer('Make2D')

            # 3. Compare and remove overlapping Curves
            args = {k: [] for k in 'ab'}

            for l in baseLayers:
                for child in ('lines', 'tangents'):
                    a = layer(view, 'visible', child, 0, l)
                    b = layer(view, 'visible', child, 1, l)

                    for var in 'ab':
                        l2 = eval(var)

                        if rs.IsLayer(l2):
                            Visible(l2, True)
                            args[var].extend(rs.ObjectsByLayer(l2))

            RemoveOverlappingCurves(*args.values())
