import json
import uuid
import os
import tempfile
import shutil
from typing import Any

from sage.all import QQ, PolynomialRing, MatrixSpace
from sage.rings import polynomial
from sage.matrix import matrix_space, matrix_rational_dense
from sage.rings.polynomial.multi_polynomial_ideal import MPolynomialIdeal
from sage.rings.polynomial.multi_polynomial_libsingular import (
    MPolynomialRing_libsingular,
    MPolynomial_libsingular,
)

VERSION_NUMBER = (1, 5, 0)

################################################################################
# Global serializer state

class GlobalSerializerState:
    def __init__(self):
        self.obj_to_id = {}
        self.id_to_obj = {}

global_serializer_state = GlobalSerializerState()

def reset_global_serializer_state():
    global_serializer_state.obj_to_id.clear()
    global_serializer_state.id_to_obj.clear()

################################################################################
# SerializerState

class SerializerState:
    def __init__(self, io, with_attrs):
        self.new_level_entry = True
        self.refs = []
        self.io = io
        self.key = None
        self.with_attrs = with_attrs

    def begin_node(self):
        if not self.new_level_entry:
            self.io.write(",")
        else:
            self.new_level_entry = False
        if self.key is not None:
            self.io.write(f"\"{self.key}\":")
            self.key = None

    def begin_dict_node(self):
        self.begin_node()
        self.io.write("{")

    def end_dict_node(self):
        self.io.write("}")
        if self.new_level_entry:
            self.new_level_entry = False

    def begin_array_node(self):
        self.begin_node()
        self.io.write("[")

    def end_array_node(self):
        self.io.write("]")
        if self.new_level_entry:
            self.new_level_entry = False

################################################################################
# Serialization helpers

def save_data_dict(f, s, key=None):
    if key is not None:
        s.key = key
    s.begin_dict_node()
    s.new_level_entry = True
    f()
    s.end_dict_node()

def save_data_array(f, s, key=None):
    if key is not None:
        s.key = key
    s.begin_array_node()
    s.new_level_entry = True
    f()
    s.end_array_node()

def save_data_basic(s, x, key=None):
    if key is not None:
        s.key = key
    s.begin_node()
    json.dump(str(x), s.io)

def save_data_json(s, data, key=None):
    if key is not None:
        s.key = key
    s.begin_node()
    s.io.write(json.dumps(data))

def save_as_ref(s, obj):
    ref = global_serializer_state.obj_to_id.get(id(obj))
    if ref is not None:
        if ref not in s.refs:
            s.refs.append(ref)
        return str(ref)
    ref = uuid.uuid4()
    global_serializer_state.obj_to_id[id(obj)] = ref
    global_serializer_state.id_to_obj[ref] = obj
    s.refs.append(ref)
    return str(ref)

def serializer_open(io, with_attrs):
    return SerializerState(io, with_attrs)

################################################################################
# Deserialization

class DeserializerState:
    def __init__(self, obj, refs=None):
        self.obj = obj
        self.key = None
        self.refs = refs

def deserializer_open(io):
    obj = json.load(io)
    refs = obj.get("_refs", None)
    return DeserializerState(obj, refs)

def load_ref(s):
    uid = uuid.UUID(s.obj)
    if uid in global_serializer_state.id_to_obj:
        return global_serializer_state.id_to_obj[uid]
    obj = s.obj
    s.obj = s.refs[str(uid)]
    ref_obj = load_typed_object(s)
    s.obj = obj
    global_serializer_state.id_to_obj[uid] = ref_obj
    global_serializer_state.obj_to_id[id(ref_obj)] = uid
    return ref_obj

################################################################################
# Namespace

def get_oscar_serialization_version():
    v = VERSION_NUMBER
    return {
        "Oscar": [
            "https://github.com/oscar-system/Oscar.jl",
            f"{v[0]}.{v[1]}.{v[2]}",
        ]
    }

################################################################################
# Type params

def save_type_params(serializer, obj):
    def save_body():
        if isinstance(obj, MPolynomialRing_libsingular):
            save_data_basic(serializer, "MPolyRing", "name")
            save_data_dict(
                lambda: save_data_basic(serializer, "QQField", "_type"),
                serializer, "params",
            )

        elif isinstance(obj, MPolynomial_libsingular):
            ref = save_as_ref(serializer, obj.parent())
            save_data_basic(serializer, "MPolyRingElem", "name")
            save_data_basic(serializer, ref, "params")

        elif isinstance(obj, MPolynomialIdeal):
            ref = save_as_ref(serializer, obj.ring())
            save_data_basic(serializer, "MPolyIdeal", "name")
            save_data_basic(serializer, ref, "params")

        elif isinstance(obj, matrix_space.MatrixSpace):
            save_data_basic(serializer, "MatSpace", "name")
            save_data_dict(
                lambda: save_data_basic(serializer, "QQField", "_type"),
                serializer, "params",
            )

        elif isinstance(obj, matrix_rational_dense.Matrix_rational_dense):
            ref = save_as_ref(serializer, obj.parent())
            save_data_basic(serializer, "MatElem", "name")
            save_data_basic(serializer, ref, "params")

    save_data_dict(save_body, serializer, key="_type")

################################################################################
# Object serializers

def _rational_to_oscar_str(r):
    if r.denominator() == 1:
        return str(r.numerator())
    return f"{r.numerator()}//{r.denominator()}"

def _poly_to_data(p):
    exponents = [list(map(str, e)) for e in p.exponents()]
    coeffs = [_rational_to_oscar_str(c) for c in p.coefficients()]
    return list(map(list, zip(exponents, coeffs)))

def save_object(serializer, obj, key=None):
    if isinstance(obj, MPolynomialRing_libsingular):
        save_data_dict(
            lambda: save_data_json(serializer, list(obj.variable_names()), "symbols"),
            serializer, key,
        )

    elif isinstance(obj, MPolynomial_libsingular):
        save_data_json(serializer, _poly_to_data(obj), key)

    elif isinstance(obj, MPolynomialIdeal):
        save_data_json(serializer, [_poly_to_data(g) for g in obj.gens()], key)

    elif isinstance(obj, matrix_space.MatrixSpace):
        def _save():
            save_data_basic(serializer, str(obj.nrows()), "nrows")
            save_data_basic(serializer, str(obj.ncols()), "ncols")
        save_data_dict(_save, serializer, key)

    elif isinstance(obj, matrix_rational_dense.Matrix_rational_dense):
        rows = [
            [_rational_to_oscar_str(obj[i, j]) for j in range(obj.ncols())]
            for i in range(obj.nrows())
        ]
        save_data_json(serializer, rows, key)

################################################################################
# Object deserializers

def _reconstruct_poly(ring, poly_data):
    p = ring.zero()
    for entry in poly_data:
        exponent_ints = [int(e) for e in entry[0]]
        monomial = ring.one()
        for i, e in enumerate(exponent_ints):
            if e != 0:
                monomial *= ring.gens()[i] ** e
        coeff = QQ(entry[1].replace("//", "/"))
        p += coeff * monomial
    return p

def load_object(deserializer, type_str, params):
    if type_str == "MPolyRingElem":
        return _reconstruct_poly(params, deserializer.obj["data"])

    elif type_str == "MPolyRing":
        var_names = list(deserializer.obj["data"]["symbols"])
        return PolynomialRing(params, names=var_names)

    elif type_str == "MPolyIdeal":
        gens = [_reconstruct_poly(params, gd) for gd in deserializer.obj["data"]]
        return params.ideal(gens)

    elif type_str == "MatSpace":
        nrows = int(deserializer.obj["data"]["nrows"])
        ncols = int(deserializer.obj["data"]["ncols"])
        return MatrixSpace(params, nrows, ncols)

    elif type_str == "MatElem":
        rows = [
            [QQ(s.replace("//", "/")) for s in row]
            for row in deserializer.obj["data"]
        ]
        return params(rows)

    elif type_str == "QQField":
        return QQ

################################################################################
# Type dispatch

def save_typed_object(serializer, obj, key=None):
    def save_body():
        save_type_params(serializer, obj)
        save_object(serializer, obj, key="data")

    if key is None:
        save_body()
    else:
        save_data_dict(save_body, serializer, key)

def handle_refs(s):
    if s.refs:
        save_data_dict(
            lambda: [
                save_typed_object(s, global_serializer_state.id_to_obj[r], key=str(r))
                for r in s.refs
            ],
            s, key="_refs",
        )

def load_type_params(s):
    if isinstance(s.obj["_type"], str):
        return {"type_str": s.obj["_type"], "params": None}

    obj = s.obj
    s.obj = obj["_type"]["params"]
    params = load_typed_object(s)
    s.obj = obj
    return {"type_str": obj["_type"]["name"], "params": params}

def load_typed_object(s):
    if isinstance(s.obj, str):
        return load_ref(s)
    type_params_dict = load_type_params(s)
    return load_object(s, **type_params_dict)

################################################################################
# High-level API

def save(io, obj, with_attrs=True):
    serializer = serializer_open(io, with_attrs)

    def save_body():
        save_data_json(serializer, get_oscar_serialization_version(), key="_ns")
        save_typed_object(serializer, obj)
        handle_refs(serializer)

    save_data_dict(save_body, serializer)

def save_file(filename: str, obj: Any, with_attrs=True):
    tmp = tempfile.NamedTemporaryFile(
        delete=False, dir=os.path.dirname(os.path.abspath(filename))
    )
    try:
        with open(tmp.name, "w") as f:
            save(f, obj, with_attrs=with_attrs)
        shutil.move(tmp.name, filename)
    except Exception:
        os.unlink(tmp.name)
        raise

def load(io):
    deserializer = deserializer_open(io)
    return load_typed_object(deserializer)

def load_file(filename: str):
    with open(filename, "r") as f:
        return load(f)
