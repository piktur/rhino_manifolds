# [Calabi Yau](https://bitbucket.org/kunst_dev/snippets)

## TODO

* [Unify Surface UV and Normal direction](http://www.rhinoscript.org/forum/1/60)
    I assume you are talking 2D here: you can use CurveCurvature() to get curvature information for a specific point on a curve. If you take the cross product of the tangent vector and the curvature vector, the resulting vector faces in negative or positive z direction, depending on you clockwise or counterclockwise curve direction.

SampleCrvsOnSrfAtBroaderPointSamples

* SurfaceCombinations:
    find unique combinations from variable names rather than comparison of the Rhino objects which may not implement equality checking.
* IntersectBreps:
    Why is it generating thousands of curves
    Remove seam intersections, these are unnecessary.
    * ConvertToBeziers will give us the curves across self intersections. We can generate these bezier
    surfaces with the command and we can traverse the point grid to create a number of cells with which we will subdivide the surface.

    As for lower the number of isocurves we could run the pointsBuilder with smaller UV divisions and build the PointGrid from that Then feed extract interpolated curve from our surface at these points.

    Refer to Downloads/Divide_surface_rectangles.ghx for alternate isocurve generation methods.
* Border:
    We found that Border curves weren't aligned with the surfaces. We can't use curves generated from Points alone. They must be obtained from the suraces instead. Use ExtractBorder or Edges or whatever instead

* Create Subdivisions along the surface
  Intersect
  Select necessary curves delete the rest
  PointsOn, SElectPoints and then CurveThroughPoints
  We may need to do this for 2 div surfaces as well

* Create Isocurves
  Run Intersection in both directions
  Then select subsurfaces within proximity of these points
  Then run intersection on these subsurfaces.

## Review

* 1 Degree Surfaces will often span multiple divisions. `ConvertToBezier` with Degree > 2 Nurbs Surfaces
* Mesh CatmullClark produces smoother geometry, but can only be converted to 2D from Rhino for Windows 6 and output is erratic

---

* Demonstrate Make2d
* Demonstrate Export to Illustrator
* Demonstrate advanced Make2d ops for varied lineweight
* Compare Rhino 6 results
* Compare WireMesh to Bezier

---

Copy `./Libraries` Grasshopper plugins to
`~/Library/Application Support/McNeel/Rhinoceros/MacPlugIns/Grasshopper/Libraries`

---

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

> -- <cite>[Hanson, Andrew J.][1]</cite>

[Additional References](https://www.semanticscholar.org/paper/A-Construction-for-Computer-Visualization-of-Certa-Hanson/8861c0026a89af89b19e9df7267846ec056461c1?citingPapersSort=is-influential&citingPapersLimit=10&citingPapersOffset=10&citedPapersSort=is-influential&citedPapersLimit=10&citedPapersOffset=0)

---

## Tools

### Text Editor

Install [Atom](https://atom.io/). Enable `Python` syntax and install [`linter-mathematica`](https://atom.io/packages/linter-mathematica) and [`rhino-python`](https://atom.io/packages/rhino-python) Syntax Packages.

### Wolfram

[Wolfram Programming Lab](https://lab.open.wolframcloud.com/app/view/newNotebook?ext=nb) provides free Mathematica sandpit.

### [Sketchup]()

### [Rhino](http://www.rhino3d.com/download/rhino-for-mac/5/wip)

---

## Examples

### Rhino

* [1](http://developer.rhino3d.com/guides/rhinopython/primer-101/)

1. [Points](/lib/calabi/manifold.py) [[Source](http://www.tanjiasi.com/surface-design/)]

```python
    # lib/calabi_yau/manifold.py

    def __init__(*args):
        # ...
        self.Phases = []

        # NOTE [Figure 5](https://www.cs.indiana.edu/~hansona/papers/CP2-94.pdf)
        # Demonstrates phase occurrence. Build algorithm to group accordingly.
        for i, k1 in enumerate(self.RngK):
            for i, k2 in enumerate(self.RngK):
                self.Phases.append([k1, k2])
```

```python
    # lib/calabi_yau/calc.py

    PointAnalysis = {'Seq': {}}

    def Seq(cy, point, k1, k2, xi, theta):
        '''
        Collect phase paramater pairs for patches with same start/end point
        '''
        _ = Report
        OffsetX, OffsetY = cy.Offset
        x, y, z = point  # reference point

        try:
            arr = _['Seq'][(x, y, z)]
        except KeyError:
            arr = _['Seq'][(x, y, z)] = []

        def Point(cy, *args):
            x, y, z = map(
                lambda i: (i * cy.Scale),
                Calculate(cy.n, cy.Alpha, *args)  # args[1:]
            )
            x = x + OffsetX
            y = y + OffsetY

            return x, y, z

        for _k1 in cy.RngK:
            for _k2 in cy.RngK:
                # Should remake range beginning from k1, this will do for now.
                # if (k1, k2) == (_k1, _k2):
                #     return

                if (x, y, z) == Point(cy, _k1, _k2, xi, theta) or (x, y, z) == Point(cy, _k1, _k2, -1, theta):
                    arr.append((_k1, _k2))

    def Experiment(cy, k1, k2, xi, theta, point):
        _ = PointAnalysis

        result = ((U1(xi, theta) ** 2) + (U2(xi, theta) ** 2))
        if result.real == 1:
            rs.AddTextDot('1', point)  #  'u1(xi, theta) ** 2 + u2(xi, theta) ** 2 = 1'

        if _['centre']:
            rs.AddTextDot('Centre', point)

        if _['z0'].real == 1 or _['z0'].real == -1:
            rs.AddPoint(point)

        if _['theta == 0']:
            if _['minU']:
                rs.AddTextDot('(theta, xi) = (0, {0})'.format(xi), point)

            # Point of convergence "hyperbolic pie chart"
            if _['midU']:
                rs.AddTextDot('(theta, xi) = (0, 0)', point)

            if _['maxU']:
                Seq(cy, point, k1, k2, xi, theta)
                rs.AddTextDot('(theta, xi) = (0, {0})'.format(xi), point)

        if _['theta == 45']:
            rs.AddTextDot('(theta, xi) = (pi/2, 0)', point)
```

### Processing.py

* [createGraphics()](http://py.processing.org/reference/createGraphics.html)
* [PDF Export](https://www.processing.org/reference/libraries/pdf/index.html)
* [Rhino > Processing](https://www.cs.rpi.edu/~cutler/gaudi/objImport/html/objectImport.html)

### Mathematica

1. [Wolfram Mathematica - Calabi Yau Manifold](/examples/mathematica/plot_1.nb)  [[Source](http://demonstrations.wolfram.com/CalabiYauSpace/)]
2. [Wolfram Mathematica - Calabi Yau Manifold](/examples/mathematica/plot_2.nb)  [[Source](http://kaurov.com/wordpress/?p=1246)]

### SketchUp

[Ruby API Documentation](http://ruby.sketchup.com/Sketchup/)

Install [Artisan](http://artisan4sketchup.com/) plugin.

1. [Calabi](https://3dwarehouse.sketchup.com/model/73d1a448bc4c446d8389babcf188871/Manifolds)

```ruby
# Explode
# Select All
# Artisan > Subdivide & Soften
# Window > Ruby Console

Sketchup.active_model.selection
  .select { |e| e.is_a?(Sketchup::Edge) && e.soft? } # Select soft edges
  .each { |e| e.soft = false } # Disable softening
```

Modify appearance with `Window > Styles`

## Browsing Rhino Plugins source

[mcneel/rhinocommon](https://github.com/mcneel/rhinocommon)

Rhino application files are accessible from: `/Applications/RhinoWIP.app/Contents/Resources/ManagedPlugIns`

[Install Weaverbird](http://www.grasshopper3d.com/group/weaverbird/forum/topics/weaverbird-for-the-mac) Mesh optimisation plugin for Grasshopper.

---

* [#1] Transpose Complex Ops
* [#2] Decompile Assembly

[1]:https://pdfs.semanticscholar.org/a51f/16741a6452effe2c3773577484fc88948f40.pdf

Rhino
1. SelectAll
2. Export Selected .ai
3. Set Scale 1 * UnitSystem == 1mm

4. Open Exported File
5. New from Template `A4_4Div.ait` `Applications/Adobe Illustrator CC 2017/Cool Extras/en_GB/Templates`
6. Copy linework to template
7. SelectAll
8. Group
9. Resize and place within artboards

File > Document Setup
Edit Artboards if necessary (Template should already provide adequate artboards)
A4 210 * 297
A4 210 * 210 [Square]
A4 148.25 * 210
A4 105 * 105 [Square]

Export to `.psd`
Flat image: True
Resolution: 300ppi
Color Model: Grayscale or CMYK
AntiAlias: Art Optimised

Why:
  * Transparent background
  * Rasterized at correct scale
  * Layers:
    * IsoCurves
    * Rails
    * Silhouette

Object > Rasterize
