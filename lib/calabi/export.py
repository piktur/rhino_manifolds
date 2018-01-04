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

Apparently Top View + Export Selected is better suited to line export [Source](https://discourse.mcneel.com/t/exporting-in-eps-ai-format/37015)

`RhinoDLR_Python.rhp/RssLib/rhinoscript/userinterface.py@1140` `SaveFileName()`
[Example](http://developer.rhino3d.com/samples/rhinopython/export-points/)

`RhinoDLR_Python.rhp/RssLib/rhinoscript/document.py` Configure Document settings

`RhinoDLR_Python.rhp/RssLib/rhinoscript/view.py` Configure View settings:

- `RotateCamera()`

- `RotateView()`
'''
