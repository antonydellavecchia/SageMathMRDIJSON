"""Load files written by Oscar 1.9 (mrdi namespace 1.0.0); see oscar/generate.jl."""
import os

import pytest
from sage.all import QQ, ZZ, GF, Integers, PolynomialRing, SymmetricGroup, matrix

from mrdi import load_file

OSCAR_DIR = os.path.join(os.path.dirname(__file__), "oscar")


def load(name):
    return load_file(os.path.join(OSCAR_DIR, name + ".mrdi"))


def test_basic():
    assert load("int") == 42 and load("int").parent() is ZZ
    assert load("rat") == QQ(-3) / 2
    assert load("ZZ") is ZZ and load("QQ") is QQ


def test_polynomials():
    p = load("mpoly")
    x, y = p.parent().gens()
    assert p.parent().variable_names() == ("x", "y")
    assert p == x**2 * y - QQ(3) / 2 * y + 5
    t = load("upoly").parent().gen()
    assert load("upoly") == t**2 - QQ(3) / 2 * t + 5
    I = load("ideal")
    x, y = I.ring().gens()
    assert I == I.ring().ideal([x**2, y - 1])


def test_finite_fields():
    assert load("gfp") == GF(7)
    assert load("gfp_elem") == GF(7)(3)
    F = load("fq")
    assert F.order() == 4
    assert load("fq_elem") == load("fq_elem").parent().gen() + 1
    assert load("zmod") == Integers(5)
    assert load("zmod_elem") == Integers(5)(3)


def test_number_field():
    a = load("nf_elem")
    K = a.parent()
    assert K.defining_polynomial().list() == [-2, 0, 1]
    assert a == K.gen() + 1


def test_matrix_and_groups():
    assert load("mat") == matrix(QQ, [[1, 2], [3, 4]])
    assert load("permgroup").order() == 6
    assert load("perm") == SymmetricGroup(3)("(1,2,3)")


@pytest.mark.parametrize("name", sorted(f[:-5] for f in os.listdir(OSCAR_DIR) if f.endswith(".mrdi")))
def test_resave_matches_oscar_types(name, tmp_path):
    """Saving what we loaded writes the same _type names and namespaces as Oscar."""
    import json
    from mrdi import save_file, reset_global_serializer_state

    def types(d):
        if isinstance(d, dict):
            t = d.get("_type")
            here = [(t if isinstance(t, str) else (t.get("name"), t.get("_ns")))] if t else []
            return here + sum((types(v) for k, v in d.items() if k not in ("attrs",)), [])
        if isinstance(d, list):
            return sum((types(v) for v in d), [])
        return []

    oscar = json.load(open(os.path.join(OSCAR_DIR, name + ".mrdi")))
    obj = load(name)
    reset_global_serializer_state()
    save_file(str(tmp_path / "x.mrdi"), obj)
    ours = json.load(open(tmp_path / "x.mrdi"))
    assert sorted(map(str, types(ours))) == sorted(map(str, types(oscar)))
    assert set(ours["_ns"]) == {"Oscar", "mrdi"}
