"""
Serializers for field types.
Mirrors Oscar.jl's Serialization/Fields.jl.

Registered types:
  fpField / FpField  ↔  sage FiniteField_prime_modn (alias "FiniteField")
  fpFieldElem        ↔  sage IntegerMod_abstract with FiniteField parent
  FqField            ↔  sage FiniteField_givaro / FiniteField_ntl_gf2e
                          (alias "FiniteField")
  FqFieldElem        ↔  sage FiniteField_givaroElement etc.
  AbsSimpleNumField  ↔  sage NumberField (absolute, simple)
  AbsSimpleNumFieldElem ↔ sage NumberFieldElement
"""

from sage.all import QQ, ZZ, GF, NumberField, PolynomialRing
from sage.rings.finite_rings.finite_field_prime_modn import FiniteField_prime_modn
from sage.rings.finite_rings.finite_field_givaro import FiniteField_givaro
from sage.rings.finite_rings.finite_field_base import FiniteField
from sage.rings.finite_rings.integer_mod import IntegerMod_abstract
from sage.rings.number_field.number_field_base import NumberField as NumberFieldBase
from sage.rings.number_field.number_field_element import NumberFieldElement

from mrdi.core import (
    register, save_data_basic, save_data_json, save_data_dict,
    get_params_inline, get_params_ref,
)
from mrdi.rings import _rational_to_oscar_str, _reconstruct_poly_uni

# ---------------------------------------------------------------------------
# Helper: poly data for elements over QQ used as def_pol

def _uni_poly_to_data(p) -> list:
    return [[str(e), _rational_to_oscar_str(c)]
            for e, c in zip(p.exponents(), p.coefficients())]

# ---------------------------------------------------------------------------
# fpField / FpField  (GF(p) for prime p, alias "FiniteField")

def _save_fp_field(s, obj, key):
    save_data_basic(s, str(obj.characteristic()), key)

def _load_fp_field(s, params):
    p = int(s.obj.get("data", s.obj))
    return GF(p)

register(
    FiniteField_prime_modn, "FiniteField",
    save_data=_save_fp_field,
    load_fn=_load_fp_field,
)

# ---------------------------------------------------------------------------
# fpFieldElem  (element of GF(p))
# NOTE: IntegerMod_abstract is also used by ZZModRingElem; core._find_handler
# disambiguates by checking parent type.

def _get_params_fp_elem(s, obj):
    get_params_ref(s, obj.parent())

def _save_fp_elem(s, obj, key):
    save_data_basic(s, str(int(obj)), key)

def _load_fp_elem(s, params):
    raw = s.obj.get("data", s.obj)
    return params(int(raw))

# Registered under "fpFieldElem" so _find_handler (which special-cases
# IntegerMod_abstract + FiniteField parent) can find it.
from mrdi.core import _load_handlers, TypeHandler

_fp_field_elem_handler = TypeHandler(
    oscar_name="fpFieldElem",
    uses_id=False,
    get_params=_get_params_fp_elem,
    save_data=_save_fp_elem,
    load_fn=_load_fp_elem,
)
_load_handlers["fpFieldElem"] = _fp_field_elem_handler

# ---------------------------------------------------------------------------
# FqField  (GF(p^n) for n > 1, alias "FiniteField")
# Disambiguate from fpField on load by checking order vs characteristic.

def _get_params_fq_field(s, obj):
    get_params_inline(s, GF(obj.characteristic()))

def _save_fq_field(s, obj, key):
    # Save the defining polynomial for the extension
    modulus = obj.modulus()  # poly over GF(p)
    # convert coefficients to integers for portability
    data = {"degree": str(obj.degree()),
            "def_pol": [[str(e), str(int(c))]
                        for e, c in zip(modulus.exponents(),
                                        modulus.coefficients())]}
    save_data_json(s, data, key)

def _load_fq_field(s, params):
    # params is GF(p) (the base prime field)
    data = s.obj.get("data", s.obj)
    if isinstance(data, str):
        # Simple prime field stored as characteristic (shouldn't reach here)
        return GF(int(data))
    p = params.characteristic()
    n = int(data["degree"])
    if n == 1:
        return GF(p)
    Fp = GF(p)
    Fpx = PolynomialRing(Fp, 'x')
    x = Fpx.gen()
    def_pol = Fpx.zero()
    for entry in data["def_pol"]:
        exp = int(entry[0])
        coeff = Fp(int(entry[1]))
        def_pol += coeff * x ** exp
    return GF(p**n, name='z', modulus=def_pol)

register(
    FiniteField_givaro, "FqField",
    get_params=_get_params_fq_field,
    save_data=_save_fq_field,
    load_fn=_load_fq_field,
)

# Also register the element type for FqField
from sage.rings.finite_rings.element_givaro import FiniteField_givaroElement

def _get_params_fq_elem(s, obj):
    get_params_ref(s, obj.parent())

def _save_fq_elem(s, obj, key):
    save_data_basic(s, str(obj.to_integer()), key)

def _load_fq_elem(s, params):
    raw = s.obj.get("data", s.obj)
    return params.from_integer(int(raw))

register(
    FiniteField_givaroElement, "FqFieldElem",
    get_params=_get_params_fq_elem,
    save_data=_save_fq_elem,
    load_fn=_load_fq_elem,
)

# ---------------------------------------------------------------------------
# AbsSimpleNumField  (absolute simple number field, uses_id)

def _save_num_field(s, obj, key):
    def _write():
        def_pol_data = _uni_poly_to_data(obj.defining_polynomial())
        save_data_json(s, def_pol_data, "def_pol")
        save_data_basic(s, obj.variable_name(), "var")
    save_data_dict(_write, s, key)

def _load_num_field(s, params):
    data = s.obj["data"]
    Rx = PolynomialRing(QQ, "x")
    def_pol = _reconstruct_poly_uni(Rx, data["def_pol"])
    return NumberField(def_pol, data["var"])

register(
    NumberFieldBase, "AbsSimpleNumField",
    uses_id=True,
    save_data=_save_num_field,
    load_fn=_load_num_field,
)

# ---------------------------------------------------------------------------
# AbsSimpleNumFieldElem

def _get_params_nf_elem(s, obj):
    get_params_ref(s, obj.parent())

def _save_nf_elem(s, obj, key):
    # Store as list of QQ coefficients (constant term first)
    coeffs = [_rational_to_oscar_str(c) for c in obj.list()]
    save_data_json(s, coeffs, key)

def _load_nf_elem(s, params):
    K = params
    coeffs_raw = s.obj.get("data", s.obj)
    coeffs = [QQ(c.replace("//", "/")) for c in coeffs_raw]
    return K(coeffs)

register(
    NumberFieldElement, "AbsSimpleNumFieldElem",
    get_params=_get_params_nf_elem,
    save_data=_save_nf_elem,
    load_fn=_load_nf_elem,
)
