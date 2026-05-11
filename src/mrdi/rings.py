"""
Serializers for ring types.
Mirrors Oscar.jl's Serialization/Rings.jl.

Registered types:
  ZZRing      ↔  sage IntegerRing_class       (ZZ)
  QQField     ↔  sage RationalField            (QQ)
  ZZModRing   ↔  sage IntegerModRing_generic
  ZZModRingElem ↔ sage IntegerMod_abstract (non-GF parent)
  PolyRing    ↔  sage PolynomialRing_field (univariate over QQ)
  PolyRingElem ↔ sage Polynomial_rational_flint
  MPolyRing   ↔  sage MPolynomialRing_libsingular
  MPolyRingElem ↔ sage MPolynomial_libsingular
  MPolyIdeal  ↔  sage MPolynomialIdeal
  MatSpace    ↔  sage MatrixSpace
  MatElem     ↔  sage Matrix_rational_dense
"""

from sage.all import QQ, ZZ, PolynomialRing, MatrixSpace
from sage.rings.integer_ring import IntegerRing_class
from sage.rings.rational_field import RationalField
from sage.rings.polynomial.polynomial_ring import PolynomialRing_field
from sage.rings.polynomial.polynomial_rational_flint import Polynomial_rational_flint
from sage.rings.polynomial.multi_polynomial_libsingular import (
    MPolynomialRing_libsingular,
    MPolynomial_libsingular,
)
from sage.rings.polynomial.multi_polynomial_ideal import MPolynomialIdeal
from sage.rings.finite_rings.integer_mod_ring import IntegerModRing_generic
from sage.rings.finite_rings.integer_mod import IntegerMod_abstract
from sage.matrix import matrix_space, matrix_rational_dense

from mrdi.core import (
    register, save_data_basic, save_data_json, save_data_dict,
    get_params_inline, get_params_ref, _write_inline_typed_object,
)

# ---------------------------------------------------------------------------
# Helpers

def _rational_to_oscar_str(r) -> str:
    if r.denominator() == 1:
        return str(r.numerator())
    return f"{r.numerator()}//{r.denominator()}"

def _poly_to_data(p) -> list:
    """Encode a poly as [[exponent_strs, coeff_str], ...] (multivariate) or
    [[exp_str, coeff_str], ...] (univariate)."""
    if hasattr(p, 'exponents') and hasattr(p.parent(), 'ngens') and p.parent().ngens() > 1:
        exponents = [list(map(str, e)) for e in p.exponents()]
    else:
        exponents = [str(e) for e in p.exponents()]
    coeffs = [_rational_to_oscar_str(c) for c in p.coefficients()]
    return list(map(list, zip(exponents, coeffs)))

def _reconstruct_poly_multi(ring, data) -> object:
    p = ring.zero()
    for entry in data:
        exp_ints = [int(e) for e in entry[0]]
        mono = ring.one()
        for i, e in enumerate(exp_ints):
            if e:
                mono *= ring.gens()[i] ** e
        coeff = QQ(entry[1].replace("//", "/"))
        p += coeff * mono
    return p

def _reconstruct_poly_uni(ring, data) -> object:
    p = ring.zero()
    x = ring.gen()
    for entry in data:
        exp = int(entry[0])
        coeff = QQ(entry[1].replace("//", "/"))
        p += coeff * x ** exp
    return p

# ---------------------------------------------------------------------------
# ZZRing  (singleton)

def _load_zz_ring(s, params):
    return ZZ

register(
    IntegerRing_class, "ZZRing",
    load_fn=_load_zz_ring,
)

# ---------------------------------------------------------------------------
# QQField  (singleton)

def _load_qq_field(s, params):
    return QQ

register(
    RationalField, "QQField",
    load_fn=_load_qq_field,
)

# ---------------------------------------------------------------------------
# ZZModRing  (Integers(n))

def _save_zzmod_ring(s, obj, key):
    save_data_basic(s, str(obj.order()), key)

def _load_zzmod_ring(s, params):
    from sage.all import Integers
    n = int(s.obj.get("data", s.obj))
    return Integers(n)

register(
    IntegerModRing_generic, "ZZModRing",
    save_data=_save_zzmod_ring,
    load_fn=_load_zzmod_ring,
)

# ---------------------------------------------------------------------------
# ZZModRingElem  (element of Integers(n), not GF(p))

def _save_zzmod_elem(s, obj, key):
    save_data_basic(s, str(int(obj)), key)

def _get_params_zzmod_elem(s, obj):
    get_params_ref(s, obj.parent())

def _load_zzmod_elem(s, params):
    raw = s.obj.get("data", s.obj)
    return params(int(raw))

register(
    IntegerMod_abstract, "ZZModRingElem",
    get_params=_get_params_zzmod_elem,
    save_data=_save_zzmod_elem,
    load_fn=_load_zzmod_elem,
)

# ---------------------------------------------------------------------------
# PolyRing  (univariate polynomial ring, uses_id)

def _get_params_poly_ring(s, obj):
    get_params_inline(s, obj.base_ring())

def _save_poly_ring(s, obj, key):
    save_data_dict(
        lambda: save_data_json(s, [str(obj.variable_name())], "symbols"),
        s, key,
    )

def _load_poly_ring(s, params):
    symbols = s.obj["data"]["symbols"]
    return PolynomialRing(params, names=list(symbols))

register(
    PolynomialRing_field, "PolyRing",
    uses_id=True,
    get_params=_get_params_poly_ring,
    save_data=_save_poly_ring,
    load_fn=_load_poly_ring,
)

# ---------------------------------------------------------------------------
# PolyRingElem  (univariate polynomial element)

def _get_params_poly_elem(s, obj):
    get_params_ref(s, obj.parent())

def _save_poly_elem(s, obj, key):
    data = [[str(e), _rational_to_oscar_str(c)]
            for e, c in zip(obj.exponents(), obj.coefficients())]
    save_data_json(s, data, key)

def _load_poly_elem(s, params):
    return _reconstruct_poly_uni(params, s.obj.get("data", s.obj))

register(
    Polynomial_rational_flint, "PolyRingElem",
    get_params=_get_params_poly_elem,
    save_data=_save_poly_elem,
    load_fn=_load_poly_elem,
)

# ---------------------------------------------------------------------------
# MPolyRing  (multivariate polynomial ring, uses_id)

def _get_params_mpoly_ring(s, obj):
    get_params_inline(s, obj.base_ring())

def _save_mpoly_ring(s, obj, key):
    save_data_dict(
        lambda: save_data_json(s, list(obj.variable_names()), "symbols"),
        s, key,
    )

def _load_mpoly_ring(s, params):
    var_names = list(s.obj["data"]["symbols"])
    return PolynomialRing(params, names=var_names)

register(
    MPolynomialRing_libsingular, "MPolyRing",
    uses_id=True,
    get_params=_get_params_mpoly_ring,
    save_data=_save_mpoly_ring,
    load_fn=_load_mpoly_ring,
)

# ---------------------------------------------------------------------------
# MPolyRingElem

def _get_params_mpoly_elem(s, obj):
    get_params_ref(s, obj.parent())

def _save_mpoly_elem(s, obj, key):
    save_data_json(s, _poly_to_data(obj), key)

def _load_mpoly_elem(s, params):
    return _reconstruct_poly_multi(params, s.obj.get("data", s.obj))

register(
    MPolynomial_libsingular, "MPolyRingElem",
    get_params=_get_params_mpoly_elem,
    save_data=_save_mpoly_elem,
    load_fn=_load_mpoly_elem,
)

# ---------------------------------------------------------------------------
# MPolyIdeal

def _get_params_mpoly_ideal(s, obj):
    get_params_ref(s, obj.ring())

def _save_mpoly_ideal(s, obj, key):
    save_data_json(s, [_poly_to_data(g) for g in obj.gens()], key)

def _load_mpoly_ideal(s, params):
    gens = [_reconstruct_poly_multi(params, gd) for gd in s.obj.get("data", s.obj)]
    return params.ideal(gens)

register(
    MPolynomialIdeal, "MPolyIdeal",
    get_params=_get_params_mpoly_ideal,
    save_data=_save_mpoly_ideal,
    load_fn=_load_mpoly_ideal,
)

# ---------------------------------------------------------------------------
# MatSpace  (uses_id)

def _get_params_matspace(s, obj):
    get_params_inline(s, obj.base_ring())

def _save_matspace(s, obj, key):
    def _write():
        save_data_basic(s, str(obj.nrows()), "nrows")
        save_data_basic(s, str(obj.ncols()), "ncols")
    save_data_dict(_write, s, key)

def _load_matspace(s, params):
    nrows = int(s.obj["data"]["nrows"])
    ncols = int(s.obj["data"]["ncols"])
    return MatrixSpace(params, nrows, ncols)

register(
    matrix_space.MatrixSpace, "MatSpace",
    uses_id=True,
    get_params=_get_params_matspace,
    save_data=_save_matspace,
    load_fn=_load_matspace,
)

# ---------------------------------------------------------------------------
# MatElem

def _get_params_mat_elem(s, obj):
    get_params_ref(s, obj.parent())

def _save_mat_elem(s, obj, key):
    rows = [
        [_rational_to_oscar_str(obj[i, j]) for j in range(obj.ncols())]
        for i in range(obj.nrows())
    ]
    save_data_json(s, rows, key)

def _load_mat_elem(s, params):
    rows = [
        [QQ(cell.replace("//", "/")) for cell in row]
        for row in s.obj.get("data", s.obj)
    ]
    return params(rows)

register(
    matrix_rational_dense.Matrix_rational_dense, "MatElem",
    get_params=_get_params_mat_elem,
    save_data=_save_mat_elem,
    load_fn=_load_mat_elem,
)
