# KunstDev

[Snippets](https://bitbucket.org/kunst_dev/snippets)

## Resources

[Wolfram Programming Lab](https://lab.open.wolframcloud.com/app/view/newNotebook?ext=nb) provides free Mathematica sandpit.

## Tools

### Text Editor

Preferred [Atom](https://atom.io/)

### Python

### Ruby


## Snippets

1. [Wolfram Mathematica - Calabi Yau Manifold](/src/master/lib/calabi/parametric_plot_3d.nb)
  [See](http://kaurov.com/wordpress/?p=1246)


## SketchUp

[Sketchup Ruby Docs](http://ruby.sketchup.com/Sketchup/)
[Artisan](http://artisan4sketchup.com/)

### Examples

[Calabi](https://3dwarehouse.sketchup.com/model/73d1a448bc4c446d8389babcf188871/Manifolds)

```
Explode
Select All
Artisan > Subdivide & Soften
Window > Ruby Console

Sketchup.active_model.selection
  .select { |e| e.is_a?(Sketchup::Edge) && e.soft? } # Select soft edges
  .each { |e| e.soft = false } # Disable softening
```
