'''

[Autodesk Maya - Vector Render demonstration](https://vimeo.com/15790213)
Vector formats not available to Trail users.

1. Export NURBS Surfaces as "IGES" from Rhino
2. Import exported iges into Maya
3. You may need to reverse surface direction Surfaces > Reverse Dirction
4. Go to Render > Render Settings
5. Select Maya Vector
6. Setup vector output
7. Disable Fill objects
8. Enable Edges objects and configure setting
9. `Render View` or `Batch Render`

Export Points to File. Useful in cases where we might wish to generate models from the points array with tools other than Rhino.
`~/Library/Application Support/McNeel/Rhinoceros/Scripts/samples/ExportPoints.py`

```

    SetupView()
    step = 15 # ensure multiple of 15

    for dimension in range(10):
        plot.Run()
        selectAll()

        # No need to export at both 0 and 360deg
        for i in range((360 / step) - 1):
            rotation = i * step
            f = '_'.join(['CY', str(dimension), str(rotation)])
            ext = 'eps' # eps|ai|dwg
            RotateView(rotation)
            SaveView(f, ext)

        ClearView()
        ResetRotation()

```

- `DupBorder` Surfaces
- `Intersection`
- `DupBorder` PolySurface
- `Sillhouette`
- `Extract Wiremesh`
- `Extract Isocurves`
- From `Perspective` position camera and `SelAll`
- [`Make2D`](http://docs.mcneel.com/rhino/5/help/en-us/commands/make2d.htm) select "Current View" and select relevant layers lines etc to display. NOTE When using Make2d create a new layer for 2D and assign 2D Objects to it. Otherwise display will be linked to the source layer.
- `SelCrv` and `File > Export Selected`. Use *.ai. Experiment with scale. Use CMYK Save.

ExtractWireframe or ExtractIsoCurves for manual selection
We can increase the number of curves from ExtractWireframe by selecting the surface and toggled object property isocurves
Select Surface
Select Intersections
Make2D
Use Maintain Source Layers to keep everything seperate

AI files are comaptible with Illustrator only.

Thorough tut on export AI layers
https://vimeo.com/channels/rhino/52298871
https://vimeo.com/channels/rhino/74593679
https://vimeo.com/channels/rhino/52298042

`Sillhouette` may be interesting too, but it does some weird things when delimiting non surface edges. Maybe use a cutout instead
`Isocurves` - `SelSrf` then go to Object Properties tab left side, (can we get at this programatically) and increase Isocurves and mesh quality etc.
`Edges` as separate layer

## Rhino.ViewProjectionXForm roughly equivalent to Make2D
[](http://developer.rhino3d.com/api/rhinoscript/view_methods/viewprojectionxform.htm)
[](http://developer.rhino3d.com/api/rhinoscript/object_methods/transformobject.htm)

[Example executing UI command programatically](https://github.com/localcode/rhinopythonscripts/blob/master/Make2D.py#L199)
(https://github.com/localcode/rhinopythonscripts)

[Alternative](https://discourse.mcneel.com/t/open-polysurface-silhouette-make2d-closed-surface-or-solid/5719/10)

[](https://docs.mcneel.com/rhino/5/help/en-us/fileio/ai_ai_export.htm)
Apparently Top View + Export Selected is better suited to line export [Source](https://discourse.mcneel.com/t/exporting-in-eps-ai-format/37015)

[](http://developer.rhino3d.com/samples/#viewports-and-views-1)
[](http://developer.rhino3d.com/samples/rhinocommon/add-layout/)
[](http://developer.rhino3d.com/samples/cpp/two-view-layout/)

`RhinoDLR_Python.rhp/RssLib/rhinoscript/userinterface.py@1140` `SaveFileName()`
[Example](http://developer.rhino3d.com/samples/rhinopython/export-points/)

`RhinoDLR_Python.rhp/RssLib/rhinoscript/document.py` Configure Document settings
`RhinoDLR_Python.rhp/RssLib/rhinoscript/object.py` Configure Object style and position
`RhinoDLR_Python.rhp/RssLib/rhinoscript/view.py` Configure View settings

[Penguin Plugin](http://www.penguin3d.com/)

- `RotateCamera()`

- `RotateView()`

## Manipulate Render Light Source
[](http://v5.rhino3d.com/forum/topics/rhino-5-artistic-display-mode-get-flat-unshaded-render-for-a-cell?commentId=6377196%3AComment%3A129723)
[](https://www.youtube.com/watch?v=XKR-KxiSYSY)
'''

import os
import errno
import sys
import System
from System.IO import Path, File, FileInfo, FileAttributes
import System.Collections.Generic as SCG

import rhinoscriptsyntax as rs
from scriptcontext import doc
import Rhino
from Rhino.FileIO import FileWriteOptions, FileReadOptions


def Export(queue, dir='~/Documents/CY'):
    '''
    Parameters:
        queue : dict
        dir : string

    TODO you may want to CreateWireframePreviewImage to provide hint as to 3d file contents
        preview = fname('jpg', path, f)
        view = doc.Views.Find('Top', False)
        previewSize = System.Drawing.Size(100, 100)  # view.ClientRectangle.Size
        view.CreateWireframePreviewImage(preview, previewSize, True, False)
    '''
    for path in queue.iterkeys():
        obj = queue[path]
        obj.Build()
        doc.Views.Redraw()

        ExportFile(path)

        # Reset Document
        rs.Command('_SelAll')
        rs.Command('_Delete')


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


def ExportFile(filePath, version=5, geomOnly=False, selectedOnly=False):
    '''
    Export a file.
    [See](https://github.com/localcode/rhinopythonscripts/blob/34c5314/FileTools.py)
    '''
    opt = FileWriteOptions()
    opt.FileVersion = version
    opt.WriteGeometryOnly = geomOnly
    opt.WriteSelectedObjectsOnly = selectedOnly

    return doc.WriteFile(filePath, opt)


def ExportLayers(layerNames, filePath, version=4):
    '''
    Export only the items on designated layers to a file.
    [See](https://github.com/localcode/rhinopythonscripts/blob/34c5314/FileTools.py)
    '''
    # save selection
    oldSelection = rs.SelectedObjects()

    # clear selection
    rs.UnselectAllObjects()

    # add everything on the layers to selection
    for name in layerNames:
        objs = scriptcontext.doc.Objects.FindByLayer(name)
        guids = [obj.Id for obj in objs]
        scriptcontext.doc.Objects.Select.Overloads[SCG.IEnumerable[System.Guid]](guids)

    # export selected items
    exportFile(filePath, version, selectedOnly=True)

    # clear selection
    rs.UnselectAllObjects()

    # restore selection
    if oldSelection:
        scriptcontext.doc.Objects.Select.Overloads[SCG.IEnumerable[System.Guid]](oldSelection)

    # print 'exported %s' % filePath
