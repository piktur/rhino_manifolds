from System.Drawing import Color
import System.Guid.Empty
from scriptcontext import doc
import rhinoscriptsyntax as rs
import json

def Halt():
    '''
    In lieu of MacOS debugger...
    '''
    if rs.GetBoolean('Proceed',  ('Proceed?', 'No', 'Yes'), (True)) is None:
        return None


def ExportNamedViews():
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
    # TODO
    log = open('./views.json', 'a')
    data = json.loads(log)

    for fname in data.iterkeys():
        for view in data[fname].iterkeys():
            camera, target = data[fname][view]
            rs.AddNamedView(view)
            rs.ViewCameraTarget(view, camera, target)


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


def rendered(obj):
    '''
    Confirm `obj` present in document Guid
    '''
    if obj == System.Guid.Empty:
        raise Exception('RenderError')

    return True


def render(geometry, layer):
    id = doc.Objects.Add(geometry)
    rendered(id)

    if layer:
        if not rs.IsLayer(layer):
            rs.AddLayer(layer)
        rs.ObjectLayer(id, layer)

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

    def __init__(self, srf, U, V, TrimAware=True, Phase=None):
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
        self.SubSurfaces = {n: {} for n in Phase}
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

                if self.trimAware:
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
            maxV = self.V - 1  # zero offset
            countV = 0

            while countV <= maxV:
                i0 = countU * (self.V + 1) + countV
                i1 = i0 + self.V + 1
                i2 = i1 + 1
                i3 = i0 + 1

                c0, c1, c2, c3 = [
                    self.Parameters[eval('i' + str(n))] for n in self.__conf__['quad']
                ]
                edges = CurveList()
                for t in self.__conf__['combinations']:
                    arr = rs.coerce2dpointlist([eval('c' + str(n)) for n in t])
                    curve = self.Surface.InterpolatedCurveOnSurfaceUV(arr, tolerance)
                    edges.Add(curve)

                subSrf, err = NurbsSurface.CreateNetworkSurface(
                    edges,
                    3,
                    0.1,
                    0.1,
                    1.0
                )

                self.SubSurfaces[i][j] = subSrf
                __path__(self.Phase + (i, j))

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
            self.SubSurfaces[i] = {}

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
                id = doc.Objects.AddSurface(subSrf)

                self.SubSurfaces[i][j] = subSrf
                __path__(self.Phase + (i, j))

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
