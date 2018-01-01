# KunstDev

[Snippets](https://bitbucket.org/kunst_dev/snippets)

## Resources

[Wolfram Programming Lab](https://lab.open.wolframcloud.com/app/view/newNotebook?ext=nb) provides free Mathematica sandpit.

## Tools

### Text Editor

Preferred [Atom](https://atom.io/)

### Python

1. [Wolfram Mathematica - Calabi Yau Manifold](/src/master/lib/calabi/plot_3.py)
  [See](http://www.tanjiasi.com/surface-design/)

### Ruby

## Snippets

### Mathematica

1. [Wolfram Mathematica - Calabi Yau Manifold](/src/master/lib/calabi/plot_1.nb)
  [See](http://demonstrations.wolfram.com/CalabiYauSpace/)
2. [Wolfram Mathematica - Calabi Yau Manifold](/src/master/lib/calabi/plot_2.nb)
  [See](http://kaurov.com/wordpress/?p=1246)

## SketchUp

[Sketchup Ruby Docs](http://ruby.sketchup.com/Sketchup/)
[Artisan](http://artisan4sketchup.com/)

### Examples

[Calabi](https://3dwarehouse.sketchup.com/model/73d1a448bc4c446d8389babcf188871/Manifolds)

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
