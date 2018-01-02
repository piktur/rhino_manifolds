# KunstDev

[Snippets](https://bitbucket.org/kunst_dev/snippets)

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

1. [Points](/lib/calabi/plot_3.py) [[Source](http://www.tanjiasi.com/surface-design/)]

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
