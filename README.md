# [Calabi Yau](https://bitbucket.org/kunst_dev/snippets)

A Quintic complex Fermat Surface (power n = 5) is known to provide 10-dimensional String Theory with the 6D Einstein manifold needed for the missing dimensions of Spactime!

Basic String Theory says Spacetime is 10 dimensional; we experience 4 dimensions, 3 in Space and 1 in Time. Quintic (power n = 5) polynomial Calabi Yau space.

* [1](https://www.youtube.com/watch?v=Yz6gltKeoM8)
* [2](http://scholarpedia.org/article/Calabi-Yau_manifold)
* [3](https://mathoverflow.net/questions/42707/calabi-yau-manifolds)
* [4](http://dimensions-of-time.blogspot.com.au/)
* [5](http://prideout.net/blog/?p=44)
* ["The Elegant Universe", Brian Greene]()
* ["The Fabric of the Cosmos", Brian Greene]()

## Algorithm

[Andrew J. Hanson's algorithm](https://www.cs.indiana.edu/~hansona/papers/CP2-94.pdf) and [summary](http://aleph.se/andart2/)

> Full disclosure obligates me to point out that the visualizations
in Figure 6 are vastly misleading. The full 6D manifold is
actually closed and compact, with Euler characteristic –200.
Among other subtle details, the 2D cross-section in Figure
6a should have its five circular outer edges that extend to
infinity closed up to make a surface of genus 6. Nevertheless,
the open-edged version of the quintic in Figure 6 contains
enough information to check that it’s a consistent local
depiction of the complete manifold and so is still a sufficient
(although not ideal) representation.

> -- <cite>[Hanson, Andrew J.](https://pdfs.semanticscholar.org/a51f/16741a6452effe2c3773577484fc88948f40.pdf)</cite>

[Additional References](https://www.semanticscholar.org/paper/A-Construction-for-Computer-Visualization-of-Certa-Hanson/8861c0026a89af89b19e9df7267846ec056461c1?citingPapersSort=is-influential&citingPapersLimit=10&citingPapersOffset=10&citedPapersSort=is-influential&citedPapersLimit=10&citedPapersOffset=0)

---

## Tools

* [Wolfram Programming Lab](https://lab.open.wolframcloud.com/app/view/newNotebook?ext=nb)

---

* [Rhino](http://www.rhino3d.com/download/rhino-for-mac/5/wip)

* [Rhino Primer](http://developer.rhino3d.com/guides/rhinopython/primer-101/)

* [mcneel/rhinocommon](https://github.com/mcneel/rhinocommon)

Plugins:

* `~/Applications/RhinoWIP.app/Contents/Resources/ManagedPlugIns`

* `~/Library/Application Support/McNeel/Rhinoceros/MacPlugIns/Grasshopper/Libraries`

---
Install [Atom](https://atom.io/). Enable `Python` syntax and install [`linter-mathematica`](https://atom.io/packages/linter-mathematica) and [`rhino-python`](https://atom.io/packages/rhino-python) Syntax Packages.

---

## Process

### Generate Intersection Curves

1. `RunPythonScript` [`IntersectSurfaces()`](/lib/macro/intersect_surfaces.py) to generate intersection curves

### Generate 2D View

2. `RunPythonScript` [`Make2d()`](/lib/macro/make2d.py) to generate raw 2D curves.
  1. Visible `PolySurfaces::1`
  2. Visible `Intersect::Curves`
  3. Rotate model or select the preferred view
  4. Select objects on `PolySurfaces::1` and `Intersect::Curves`
  5. Set DocumentProperties > Model > Absolute tolerance to [`0.1`](/1.png)
  6. Run [`Make2D`](/2.png)
  7. Rename `Make2D` layer
  8. Set DocumentProperties > Model > Absolute tolerance to `0.001`
  9. Run `Make2D`
  10. Visible `Curves::1::0::U`
  11. Select objects on `Curves::1::0::U`
  12. Set DocumentProperties > Model > Absolute tolerance to `0.0000000001`
  13. Run `Make2d`
  14. Invisible `Curves::1::0::U`
  15. Visible `Curves::1::0::V`
  16. Select objects on `Curves::1::0::V`
  17. Run `Make2d`
  18. Perform manual selection/correction using:
    * `Trim` by one or more cutting objects
    * `Split` by one or more cutting objects
    * `ContinueCurve` adding additional Control Points
    * `BlendCrv` to fill between two visually continuous Curves
    * `Join` continuous Curves within tolerance of each other

### Export/Import Views

1. Open source file
2. `RunPythonScript` [`ExportNamedViews()`](/lib/macro/export_named_views.py) to write view coordinates to `./views.json`
3. Create a new file
4. `RunPythonScript` ['CalabiYau.Run()'](/lib/__init__.py)
5. `RunPythonScript` [`ImportNamedViews()`](/lib/macro/import_named_views.py)

### Export Vector/Raster

1. `SelectAll` 2D Curves
2. `File > Export Selected` as Adobe Illustrator `.ai`
3. `File > Export Selected` as Rhino `.3dm`

1. `Open` exported curves with Adobe Illustrator
2. `Select All`
3. `Resize` selection so that the largest dimension measures `200mm`
4. `Drag` selection into centre of `Artboard` measuring `210x210mm`
5. Set `Stroke Width` to `0.4mm`
6. `Save As` .eps

See template: `~/Applications/Adobe Illustrator CC 2017/Cool Extras/en_GB/Templates/A4_4Div.ait`

Rasterize `File > Export > Export As` [`.psd`](/3.png)

1. Select whitespace on `5-d-4::visible::lines::PolySurfaces::1`
2. Create a New Layer at bottom of Layer stack
3. Fill selection with paper colour sample

---

## Examples

1. [Wolfram Mathematica](/examples/mathematica/plot_1.nb)  [[Source](http://demonstrations.wolfram.com/CalabiYauSpace/)]

2. [Wolfram Mathematica](/examples/mathematica/plot_2.nb)  [[Source](http://kaurov.com/wordpress/?p=1246)]

3. [Wolfram Mathematica](/examples/mathematica/plot_3.nb)

4. [Wolfram Mathematica](/examples/mathematica/plot_4.nb)

5. [Wolfram Mathematica](/examples/mathematica/plot_5.nb)

6. [Wolfram Mathematica](/examples/mathematica/plot_6.nb)

7. [SketchUp](https://3dwarehouse.sketchup.com/model/73d1a448bc4c446d8389babcf188871/Manifolds)

8. [Rhino](http://www.tanjiasi.com/surface-design/)
