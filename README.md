# sage-mrdi-serialization

Save and load Sage mathematical objects using the [MRDI](https://www.mrdi.eu/) file format (`.mrdi`), a JSON-based format designed for interoperability between computer algebra systems.

Files produced here are compatible with [Oscar.jl](https://github.com/oscar-system/Oscar.jl)'s serialization format (version 1.5).

## Supported types

| Sage type | Oscar type |
|---|---|
| `MatrixSpace(QQ, m, n)` | `MatSpace` |
| `Matrix_rational_dense` | `MatElem` |
| `MPolynomialRing_libsingular` (over QQ) | `MPolyRing` |
| `MPolynomial_libsingular` | `MPolyRingElem` |
| `MPolynomialIdeal` | `MPolyIdeal` |

## Usage

```python
from src.mrdi import save_file, load_file, reset_global_serializer_state
from sage.all import QQ, MatrixSpace, PolynomialRing

# Matrix
M = MatrixSpace(QQ, 2, 2)
m = M([[1, 2], [3, 4]])
save_file("m.mrdi", m)

reset_global_serializer_state()
m2 = load_file("m.mrdi")

# Polynomial
R = PolynomialRing(QQ, "x,y")
x, y = R.gens()
p = x**2 * y - QQ(1, 3) * x + 1
save_file("p.mrdi", p)

reset_global_serializer_state()
p2 = load_file("p.mrdi")

# Ideal
I = R.ideal([x**2 - y, x * y - 1])
save_file("I.mrdi", I)

reset_global_serializer_state()
I2 = load_file("I.mrdi")
```

> **Note:** Call `reset_global_serializer_state()` between unrelated save/load operations to clear the object reference cache.

## Running tests

```bash
conda run -n mardi-annual pytest tests/ -v
```

## Citation

If you use this project, please cite the MRDI format paper:

> Antony Della Vecchia, Michael Joswig, Benjamin Lorenz.
> **A FAIR File Format for Mathematical Software.**
> In: *Mathematical Software – ICMS 2024*, Lecture Notes in Computer Science. Springer, 2024.
> DOI: [10.1007/978-3-031-64529-7_25](https://dl.acm.org/doi/10.1007/978-3-031-64529-7_25)

## Project layout

```
src/mrdi.py    — serialization library
tests/         — pytest test suite
```
