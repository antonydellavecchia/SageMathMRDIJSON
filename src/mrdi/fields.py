"""
Serializers for field types.
Mirrors Oscar.jl's Serialization/Fields.jl.

Registered types:
  FiniteField           ↔  sage finite fields, GF(p) and GF(p^n)   (mrdi, uses_id)
  FiniteFieldElement    ↔  sage finite field elements              (mrdi)
  AbsSimpleNumField     ↔  sage NumberField (absolute, simple)     (Oscar, uses_id)
  AbsSimpleNumFieldElem ↔  sage NumberFieldElement                 (Oscar)

Like Oscar, GF(p) is written with data p and no params; GF(p^n) with params a
univariate polynomial ring over GF(p) and data its defining polynomial as
[[exponent, coefficient], ...].
"""

from sage.all import QQ, GF, NumberField, PolynomialRing
from sage.rings.finite_rings.finite_field_base import FiniteField
from sage.rings.finite_rings.element_givaro import FiniteField_givaroElement
from sage.rings.number_field.number_field_base import NumberField as NumberFieldBase
from sage.rings.number_field.number_field_element import NumberFieldElement

from mrdi.core import register, save_data_basic, save_data_json, save_data_dict
from mrdi.basic_types import rational_from_json
from mrdi.rings import _upoly_to_data, _reconstruct_poly_uni

def _int_poly_data(p) -> list:
    """[[exponent, coefficient], ...] for a poly over GF(p), as integers."""
    return [[int(e), int(c)] for e, c in zip(p.exponents(), p.coefficients())]

# ---------------------------------------------------------------------------
# FiniteField  (uses_id)

def _fq_params(F):
    return None if F.degree() == 1 else F.modulus().parent()

def _save_fq_field(s, F, key):
    if F.degree() == 1:
        save_data_json(s, int(F.characteristic()), key)
    else:
        save_data_json(s, _int_poly_data(F.modulus()), key)

def _load_fq_field(s, params):
    data = s.obj.get("data", s.obj)
    if params is None:                       # GF(p)
        return GF(int(data))
    if isinstance(data, dict):               # older files of this package
        Fp = params
        Fpx = PolynomialRing(Fp, "x")
        modulus = sum((Fp(int(c)) * Fpx.gen() ** int(e) for e, c in data["def_pol"]), Fpx.zero())
    else:                                    # params: polynomial ring over GF(p)
        Fpx = params
        modulus = sum((int(c) * Fpx.gen() ** int(e) for e, c in data), Fpx.zero())
    p = modulus.base_ring().characteristic()
    return GF(p ** modulus.degree(), name="z", modulus=modulus)

register(
    FiniteField, "FiniteField",
    uses_id=True,
    instance="FqField",
    params=_fq_params,
    save_data=_save_fq_field,
    load_fn=_load_fq_field,
)

# ---------------------------------------------------------------------------
# FiniteFieldElement
# GF(p) elements are IntegerMod_abstract; core._find_handler routes them here.

def _save_fq_elem(s, x, key):
    if x.parent().degree() == 1:
        save_data_json(s, int(x), key)
    else:
        save_data_json(s, _int_poly_data(x.polynomial()), key)

def _load_fq_elem(s, F):
    data = s.obj.get("data", s.obj)
    if isinstance(data, list):
        z = F.gen()
        return sum((int(c) * z ** int(e) for e, c in data), F.zero())
    if F.degree() == 1:
        return F(int(data))
    return F.from_integer(int(data))         # older files of this package

register(
    FiniteField_givaroElement, "FiniteFieldElement",
    params=lambda x: x.parent(),
    save_data=_save_fq_elem,
    load_fn=_load_fq_elem,
)

# ---------------------------------------------------------------------------
# AbsSimpleNumField  (uses_id)

def _save_num_field(s, K, key):
    def _write():
        save_data_json(s, _upoly_to_data(K.defining_polynomial()), "def_pol")
        save_data_basic(s, K.variable_name(), "var")
    save_data_dict(_write, s, key)

def _load_num_field(s, params):
    data = s.obj["data"]
    Rx = params if params is not None else PolynomialRing(QQ, "x")
    return NumberField(_reconstruct_poly_uni(Rx, data["def_pol"]), data["var"])

register(
    NumberFieldBase, "AbsSimpleNumField",
    uses_id=True,
    params=lambda K: K.defining_polynomial().parent(),
    save_data=_save_num_field,
    load_fn=_load_num_field,
)

# ---------------------------------------------------------------------------
# AbsSimpleNumFieldElem: [[power of generator, coeff_str], ...]

def _save_nf_elem(s, x, key):
    save_data_json(s, _upoly_to_data(x.polynomial()), key)

def _load_nf_elem(s, K):
    data = s.obj.get("data", s.obj)
    if data and not isinstance(data[0], list):   # older files: dense coefficient list
        return K([rational_from_json(c) for c in data])
    a = K.gen()
    return sum((rational_from_json(c) * a ** int(e) for e, c in data), K.zero())

register(
    NumberFieldElement, "AbsSimpleNumFieldElem",
    params=lambda x: x.parent(),
    save_data=_save_nf_elem,
    load_fn=_load_nf_elem,
)
