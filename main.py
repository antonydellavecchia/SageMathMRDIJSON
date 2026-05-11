import json
import uuid
import os
import tempfile
import shutil
from typing import Any, Dict, Tuple, Type, Union, List
from dataclasses import dataclass
from collections import defaultdict
from sage.all import QQ, PolynomialRing, MatrixSpace
from sage.rings import polynomial
from sage.matrix import matrix_space, matrix_rational_dense


################################################################################
# Type Serializers (convert type to string)
def convert_type_to_string(T):
    return str(T)

################################################################################
# Serializers
class OscarSerializer:
    pass

class JSONSerializer(OscarSerializer):
    def __init__(self, serialize_refs=True):
        self.serialize_refs = serialize_refs

class IPCSerializer(OscarSerializer):
    pass

class MultiFileSerializer(OscarSerializer):
    def __init__(self, basepath):
        self.basepath = basepath

class LPSerializer(MultiFileSerializer):
    pass

################################################################################
# Global (De)Serializer State
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
    def __init__(self, serializer, io, with_attrs):
        self.serializer = serializer
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

def save_data_json(s: SerializerState, data, key=None):
    if key is not None:
        s.key = key
        s.begin_node()

    s.io.write(json.dumps(data))

def serializer_open(io, serializer, with_attrs):
    return SerializerState(serializer, io, with_attrs)


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
    id_str = s.obj
    uid = uuid.UUID(id_str)
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
# Version info

VERSION_NUMBER = (1, 5, 0)  # Example placeholder for Oscar’s version tuple

def get_oscar_serialization_version():
    return {
        "Oscar": [
            "https://github.com/oscar-system/Oscar.jl",
            f"{VERSION_NUMBER[0]}.{VERSION_NUMBER[1]}.{VERSION_NUMBER[2]}"
        ]
    }

def save_type_params(serializer, obj):
    def save_body():
        if isinstance(obj,
                      polynomial.multi_polynomial_libsingular.MPolynomialRing_libsingular):
            save_data_basic(serializer, "MPolyRing", "name")
            save_data_dict(lambda: save_data_basic(serializer, "QQField", "_type"),
                           serializer, "params")

        elif isinstance(obj,
                        polynomial.multi_polynomial_libsingular.MPolynomial_libsingular):
            ref = save_as_ref(serializer, obj.parent())
            save_data_basic(serializer, "MPolyRingElem", "name")
            save_data_basic(serializer, ref, "params")

        elif isinstance(obj, matrix_space.MatrixSpace):
            save_data_basic(serializer, "MatSpace", "name")
            save_data_dict(lambda: save_data_basic(serializer, "QQField", "_type"),
                           serializer, "params")

        elif isinstance(obj, matrix_rational_dense.Matrix_rational_dense):
            ref = save_as_ref(serializer, obj.parent())
            save_data_basic(serializer, "MatElem", "name")
            save_data_basic(serializer, ref, "params")

    save_data_dict(save_body, serializer, key="_type")


def save_typed_object(serializer, obj, key=None):
    def save_body():
        save_type_params(serializer, obj)
        save_object(serializer, obj, key="data")

    if key is None:
        save_body()
    else:
        save_data_dict(save_body, serializer, key)

def _rational_to_oscar_str(r):
    if r.denominator() == 1:
        return str(r.numerator())
    return f"{r.numerator()}//{r.denominator()}"

def save_object(serializer, obj, key=None):
    if isinstance(obj,
                  polynomial.multi_polynomial_libsingular.MPolynomialRing_libsingular):
        save_data_dict(lambda: save_data_json(serializer, obj.variable_names(), "symbols"), serializer, key)

    elif isinstance(obj,
                    polynomial.multi_polynomial_libsingular.MPolynomial_libsingular):
        exponents = [list(map(str, e)) for e in obj.exponents()]
        coeffs = [s.replace("/", "//") for s in map(str, obj.coefficients())]
        a = list(map(list, zip(exponents, coeffs)))
        save_data_json(serializer, a, key)

    elif isinstance(obj, matrix_space.MatrixSpace):
        def _save_mat_space():
            save_data_basic(serializer, str(obj.nrows()), "nrows")
            save_data_basic(serializer, str(obj.ncols()), "ncols")
        save_data_dict(_save_mat_space, serializer, key)

    elif isinstance(obj, matrix_rational_dense.Matrix_rational_dense):
        rows = [
            [_rational_to_oscar_str(obj[i, j]) for j in range(obj.ncols())]
            for i in range(obj.nrows())
        ]
        save_data_json(serializer, rows, key)


def handle_refs(s):
    if s.refs:
        save_data_dict(lambda: [
            save_typed_object(s,
                              global_serializer_state.id_to_obj[r],
                              key=str(r)) for r in s.refs
        ], s, key="_refs")

def load_type_params(s):
    if isinstance(s.obj['_type'], str):
        return {
            'type_str': s.obj['_type'],
            'params': None
        }
    else:
        if isinstance(s.obj, str):
            params = load_ref(s)
        else:
            obj = s.obj
            s.obj = obj['_type']['params']
            params = load_typed_object(s)
            s.obj = obj
            
    return {
        'type_str': s.obj['_type']['name'],
        'params': params
        }

def load_object(deserializer, type_str, params):
    if type_str == "MPolyRingElem":
        p = QQ(0)
        for entry in deserializer.obj["data"]:
            exponent_ints = [int(i) for i in entry[0]]
            monomial = QQ(1)
            for i, e in enumerate(exponent_ints):
                if e == 0:
                    continue
                monomial *= params.gens()[i] ** e
            coeff = QQ(entry[1].replace("//", "/"))
            p += coeff * monomial
        return p

    elif type_str == "MPolyRing":
        var_names = deserializer.obj["data"]["symbols"]
        return PolynomialRing(params, len(var_names), "".join(var_names))

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
        
def load_typed_object(s):
    if isinstance(s.obj, str):
        return load_ref(s)
    
    type_params_dict = load_type_params(s)

    return load_object(s, **type_params_dict)

################################################################################
# High-level save/load

def save(io, obj, with_attrs=True):
    serializer = serializer_open(io, None, with_attrs)

    def save_body():
        # header
        save_data_json(serializer, get_oscar_serialization_version(), key="_ns")

        # save type params
        save_typed_object(serializer, obj)

        handle_refs(serializer)

    save_data_dict(save_body, serializer)

def save_file(filename: str, obj: Any, with_attrs=True):
    tmp = tempfile.NamedTemporaryFile(delete=False, dir=os.path.dirname(filename) or ".")
    with open(tmp.name, "w") as f:
        save(f, obj, with_attrs=with_attrs)
    shutil.move(tmp.name, filename)


def load(io):
    deserializer = deserializer_open(io)
    return load_typed_object(deserializer)
    

def load_file(filename: str):
    with open(filename, "r") as f:
        return load(f)


################################################################################
# Example usage

if __name__ == "__main__":
    M = MatrixSpace(QQ, 2, 3)
    m = M([[1, 2, 3], [4, 5, 6]])
    print("original:", m)

    save_file("m.mrdi", m)

    reset_global_serializer_state()
    m2 = load_file("m.mrdi")
    print("loaded:  ", m2)
    assert m == m2, "round-trip failed"
    print("round-trip OK")
    
