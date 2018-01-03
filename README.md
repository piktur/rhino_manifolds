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

[](http://developer.rhino3d.com/guides/rhinopython/primer-101/)

1. [Points](/lib/calabi/plot.py) [[Source](http://www.tanjiasi.com/surface-design/)]

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


## Math

`C#` math functions transposed to `Python`. These function seem to exist because there is no `Complex` type in `C#`.

```python
  import math, cmath

  def Abs(n):
      n = complex(n)
      return math.sqrt((n.real * n.real) + (n.imag * n.imag))


  def Arg(n):
      n = complex(n)
      if Abs(n) != 0:
          return cmath.phase(n)  # equivalent to `math.atan2(n.imag, n.real)`
      else:
          return 0

  # Use complex(0,1) ** complex(0,1)
  def Pow(n, x):
      n = Abs(n)
      if n != 0:
          n1 = x * Arg(n)
          return complex((n ** x) * cos(n1), (n ** x) * sin(n1))
      else:
          return complex(0, 0)


  def Mult(n, x):
      '''
      Equivalent to `complex(real, imag) * complex(real, imag)`
      '''
      r = (n.real * x.real) - (n.imag * x.imag)
      i = (n.real * x.imag) + (n.imag * x.real)
      return complex(r, i)
```

```python
  def Complex_z1(a, b, n, k):
      i = complex(0.0, 1.0)
      u1 = Pow(Complex_u1(a, b), (2.0 / n))
      m1 = cmath.exp(i * ((2.0 * pi * k) / n))
      return m1 * u1


  def Complex_z2(a, b, n, k):
      i = complex(0.0, 1.0)
      u2 = Pow(Complex_u2(a, b), (2.0 / n))
      m2 = cmath.exp(i * ((2.0 * pi * k) / n))
      return m2 * u2
```
