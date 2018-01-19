'''
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
