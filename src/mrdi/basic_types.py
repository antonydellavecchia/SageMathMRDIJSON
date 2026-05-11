"""
Serializers for basic scalar types.
Mirrors Oscar.jl's Serialization/basic_types.jl.

Registered types:
  ZZRingElem  ↔  sage.rings.integer.Integer
  QQFieldElem ↔  sage.rings.rational.Rational
"""

from sage.rings.integer import Integer
from sage.rings.rational import Rational
from sage.all import ZZ, QQ

from mrdi.core import register, save_data_basic, save_data_json


# ---------------------------------------------------------------------------
# ZZRingElem  (Integer)

def _save_zz_elem(s, obj, key):
    save_data_basic(s, str(obj), key)

def _load_zz_elem(s, params):
    return ZZ(s.obj.get("data", s.obj))

register(
    Integer, "ZZRingElem",
    save_data=_save_zz_elem,
    load_fn=_load_zz_elem,
)

# ---------------------------------------------------------------------------
# QQFieldElem  (Rational)

def _rational_to_str(r) -> str:
    if r.denominator() == 1:
        return str(r.numerator())
    return f"{r.numerator()}//{r.denominator()}"

def _save_qq_elem(s, obj, key):
    save_data_basic(s, _rational_to_str(obj), key)

def _load_qq_elem(s, params):
    raw = s.obj.get("data", s.obj)
    if isinstance(raw, str):
        return QQ(raw.replace("//", "/"))
    return QQ(raw)

register(
    Rational, "QQFieldElem",
    save_data=_save_qq_elem,
    load_fn=_load_qq_elem,
)
