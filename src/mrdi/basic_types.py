"""
Serializers for basic scalar types.
Mirrors Oscar.jl's Serialization/basic_types.jl.

Registered types (mrdi namespace):
  Integer   ↔  sage.rings.integer.Integer
  Rational  ↔  sage.rings.rational.Rational
"""

from sage.rings.integer import Integer
from sage.rings.rational import Rational
from sage.all import ZZ, QQ

from mrdi.core import register, save_data_basic, save_data_json


def rational_to_str(r) -> str:
    if r.denominator() == 1:
        return str(r.numerator())
    return f"{r.numerator()}//{r.denominator()}"

def rational_from_json(x):
    return QQ(x.replace("//", "/")) if isinstance(x, str) else QQ(x)


# ---------------------------------------------------------------------------
# Integer

def _save_zz_elem(s, obj, key):
    save_data_json(s, int(obj), key)

def _load_zz_elem(s, params):
    return ZZ(s.obj.get("data", s.obj))

register(
    Integer, "Integer",
    params=lambda obj: ZZ,
    save_data=_save_zz_elem,
    load_fn=_load_zz_elem,
)

# ---------------------------------------------------------------------------
# Rational

def _save_qq_elem(s, obj, key):
    save_data_basic(s, rational_to_str(obj), key)

def _load_qq_elem(s, params):
    return rational_from_json(s.obj.get("data", s.obj))

register(
    Rational, "Rational",
    params=lambda obj: QQ,
    save_data=_save_qq_elem,
    load_fn=_load_qq_elem,
)
