# KunstDev


[Snippets](https://bitbucket.org/kunst_dev/snippets)

## Calabi Yau

---
[](http://scholarpedia.org/article/Calabi-Yau_manifold)
[](https://mathoverflow.net/questions/42707/calabi-yau-manifolds)
[](http://dimensions-of-time.blogspot.com.au/)

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

[](https://www.semanticscholar.org/paper/A-Construction-for-Computer-Visualization-of-Certa-Hanson/8861c0026a89af89b19e9df7267846ec056461c1?citingPapersSort=is-influential&citingPapersLimit=10&citingPapersOffset=10&citedPapersSort=is-influential&citedPapersLimit=10&citedPapersOffset=0)


## "Parametric" Algorithm

[](http://prideout.net/blog/?p=44)

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

[](http://developer.rhino3d.com/guides/rhinopython/primer-101/)

1. [Points](/lib/calabi/manifold.py) [[Source](http://www.tanjiasi.com/surface-design/)]

### Processing.py

[createGraphics()](http://py.processing.org/reference/createGraphics.html)
[PDF Export](https://www.processing.org/reference/libraries/pdf/index.html)
[Rhino > Processing](https://www.cs.rpi.edu/~cutler/gaudi/objImport/html/objectImport.html)
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

- [#1] Transpose Complex Ops

- [#2] Decompile Assembly

[1]:https://pdfs.semanticscholar.org/a51f/16741a6452effe2c3773577484fc88948f40.pdf
