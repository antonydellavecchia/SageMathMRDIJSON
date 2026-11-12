"""
Serializers for ring types.
Mirrors Oscar.jl's Serialization/Rings.jl.

Registered types (mrdi namespace unless marked Oscar):
  Integers        ↔  sage IntegerRing_class       (ZZ)
  Rationals       ↔  sage RationalField            (QQ)
  Nemo.zzModRing / Nemo.ZZModRing  ↔  sage IntegerModRing_generic  (Oscar)
  zzModRingElem / ZZModRingElem    ↔  sage IntegerMod_abstract (non-GF parent)  (Oscar)
  PolyRing        ↔  sage PolynomialRing_field (univariate)         (Oscar)
  PolyRingElem    ↔  sage Polynomial_rational_flint                 (Oscar)
  PolynomialRing  ↔  sage MPolynomialRing_libsingular
  Polynomial      ↔  sage MPolynomial_libsingular
  MPolyIdeal      ↔  sage MPolynomialIdeal                          (Oscar)
  MatSpace        ↔  sage MatrixSpace                               (Oscar)
  MatElem         ↔  sage Matrix_rational_dense                     (Oscar)
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

from mrdi.core import register, save_data_basic, save_data_json, save_data_dict
from mrdi.basic_types import rational_to_str, rational_from_json

# ---------------------------------------------------------------------------
# Helpers

def _mpoly_to_data(p) -> list:
    """[[exponents, coeff_str], ...] for a multivariate poly over QQ."""
    return [[[int(e) for e in exps], rational_to_str(c)]
            for exps, c in zip(p.exponents(), p.coefficients())]

def _upoly_to_data(p) -> list:
    """[[exponent, coeff_str], ...] for a univariate poly over QQ."""
    return [[int(e), rational_to_str(c)]
            for e, c in zip(p.exponents(), p.coefficients())]

def _reconstruct_poly_multi(ring, data):
    gens = ring.gens()
    p = ring.zero()
    for exps, c in data:
        mono = ring.one()
        for g, e in zip(gens, exps):
            mono *= g ** int(e)
        p += rational_from_json(c) * mono
    return p

def _reconstruct_poly_uni(ring, data):
    x = ring.gen()
    return sum((rational_from_json(c) * x ** int(e) for e, c in data), ring.zero())

def _symbols_data(s, names, key):
    save_data_dict(lambda: save_data_json(s, list(names), "symbols"), s, key)

# ---------------------------------------------------------------------------
# Integers / Rationals  (singletons)

register(IntegerRing_class, "Integers", load_fn=lambda s, params: ZZ)
register(RationalField, "Rationals", load_fn=lambda s, params: QQ)

# ---------------------------------------------------------------------------
# ZZModRing  (Integers(n)); Oscar names it by whether n fits in 64 bits

def _small_modulus(R) -> bool:
    return R.order() < 2**64

def _load_zzmod_ring(s, params):
    from sage.all import Integers
    return Integers(int(s.obj.get("data", s.obj)))

register(
    IntegerModRing_generic, "Nemo.zzModRing",
    name=lambda R: "Nemo.zzModRing" if _small_modulus(R) else "Nemo.ZZModRing",
    also_loads=("Nemo.ZZModRing",),
    save_data=lambda s, obj, key: save_data_json(s, int(obj.order()), key),
    load_fn=_load_zzmod_ring,
)

# ---------------------------------------------------------------------------
# ZZModRingElem  (element of Integers(n), not GF(p))

register(
    IntegerMod_abstract, "ZZModRingElem",
    name=lambda x: "zzModRingElem" if _small_modulus(x.parent()) else "ZZModRingElem",
    also_loads=("zzModRingElem",),
    params=lambda obj: obj.parent(),
    save_data=lambda s, obj, key: save_data_basic(s, str(int(obj)), key),
    load_fn=lambda s, params: params(int(s.obj.get("data", s.obj))),
)

# ---------------------------------------------------------------------------
# PolyRing  (univariate polynomial ring, uses_id)

def _load_poly_ring(s, params):
    return PolynomialRing(params, names=list(s.obj["data"]["symbols"]))

register(
    PolynomialRing_field, "PolyRing",
    uses_id=True,
    params=lambda obj: obj.base_ring(),
    save_data=lambda s, obj, key: _symbols_data(s, [obj.variable_name()], key),
    load_fn=_load_poly_ring,
)

# ---------------------------------------------------------------------------
# PolyRingElem  (univariate polynomial element over QQ)

register(
    Polynomial_rational_flint, "PolyRingElem",
    params=lambda obj: obj.parent(),
    save_data=lambda s, obj, key: save_data_json(s, _upoly_to_data(obj), key),
    load_fn=lambda s, params: _reconstruct_poly_uni(params, s.obj.get("data", s.obj)),
)

# ---------------------------------------------------------------------------
# PolynomialRing  (multivariate polynomial ring, uses_id)

def _load_mpoly_ring(s, params):
    return PolynomialRing(params, names=list(s.obj["data"]["symbols"]))

register(
    MPolynomialRing_libsingular, "PolynomialRing",
    uses_id=True,
    params=lambda obj: obj.base_ring(),
    save_data=lambda s, obj, key: _symbols_data(s, obj.variable_names(), key),
    load_fn=_load_mpoly_ring,
)

# ---------------------------------------------------------------------------
# Polynomial

register(
    MPolynomial_libsingular, "Polynomial",
    params=lambda obj: obj.parent(),
    save_data=lambda s, obj, key: save_data_json(s, _mpoly_to_data(obj), key),
    load_fn=lambda s, params: _reconstruct_poly_multi(params, s.obj.get("data", s.obj)),
)

# ---------------------------------------------------------------------------
# MPolyIdeal

def _load_mpoly_ideal(s, params):
    return params.ideal([_reconstruct_poly_multi(params, g) for g in s.obj.get("data", s.obj)])

register(
    MPolynomialIdeal, "MPolyIdeal",
    params=lambda obj: obj.ring(),
    save_data=lambda s, obj, key: save_data_json(s, [_mpoly_to_data(g) for g in obj.gens()], key),
    load_fn=_load_mpoly_ideal,
)

# ---------------------------------------------------------------------------
# MatSpace  (uses_id)

def _save_matspace(s, obj, key):
    def _write():
        save_data_json(s, int(obj.ncols()), "ncols")
        save_data_json(s, int(obj.nrows()), "nrows")
    save_data_dict(_write, s, key)

def _load_matspace(s, params):
    data = s.obj["data"]
    return MatrixSpace(params, int(data["nrows"]), int(data["ncols"]))

register(
    matrix_space.MatrixSpace, "MatSpace",
    uses_id=True,
    params=lambda obj: obj.base_ring(),
    save_data=_save_matspace,
    load_fn=_load_matspace,
)

# ---------------------------------------------------------------------------
# MatElem  (over QQ)

def _save_mat_elem(s, obj, key):
    save_data_json(s, [[rational_to_str(c) for c in row] for row in obj.rows()], key)

def _load_mat_elem(s, params):
    return params([[rational_from_json(c) for c in row] for row in s.obj.get("data", s.obj)])

register(
    matrix_rational_dense.Matrix_rational_dense, "MatElem",
    params=lambda obj: obj.parent(),
    save_data=_save_mat_elem,
    load_fn=_load_mat_elem,
)
