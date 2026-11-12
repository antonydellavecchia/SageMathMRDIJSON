"""
Core serializer/deserializer state, registry, and dispatch.

Pattern mirrors Oscar.jl's Serialization/main.jl.
"""

import json
import uuid
import os
import tempfile
import shutil
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

VERSION_NUMBER = (1, 9, 0)

OSCAR_URL = "https://github.com/oscar-system/Oscar.jl"
MRDI_URL = "https://www.mardi4nfdi.de/mrdi"
MRDI_VERSION = "1.0.0"

# Types shared between systems (Oscar.jl src/Serialization/mrdi.jl). They are
# written without a namespace tag; every other type gets "_ns": "Oscar".
MRDI_TYPES = {
    "Boolean", "String", "Symbol", "Integers", "Integer", "Rationals",
    "Rational", "HomogeneousList", "InhomogeneousList", "Set",
    "FiniteField", "FiniteFieldElement", "PolynomialRing", "Polynomial",
}

# Names used by Oscar < 1.9 and by older versions of this package, accepted on load.
OLD_NAMES = {
    "Bool": "Boolean",
    "ZZRing": "Integers",
    "ZZRingElem": "Integer",
    "QQField": "Rationals",
    "QQFieldElem": "Rational",
    "Vector": "HomogeneousList",
    "Tuple": "InhomogeneousList",
    "FqField": "FiniteField",
    "fpField": "FiniteField",
    "FqFieldElem": "FiniteFieldElement",
    "fpFieldElem": "FiniteFieldElement",
    "MPolyRing": "PolynomialRing",
    "MPolyRingElem": "Polynomial",
    "ZZModRing": "Nemo.ZZModRing",
}

################################################################################
# Global state

class GlobalSerializerState:
    def __init__(self):
        self.obj_to_id: dict = {}
        self.id_to_obj: dict = {}

global_serializer_state = GlobalSerializerState()

def reset_global_serializer_state():
    global_serializer_state.obj_to_id.clear()
    global_serializer_state.id_to_obj.clear()

################################################################################
# Type handler registry

@dataclass
class TypeHandler:
    oscar_name: str           # for loading; saving uses name(obj) if given
    uses_id: bool
    # obj → the object written as "params" (a ref if its handler uses_id, else inline);
    # None, or returning None, means no params
    params: Optional[Callable]
    # (s, obj, key) → writes data under key; None means no data
    save_data: Optional[Callable]
    # (s, params) → Sage object
    load_fn: Callable
    # value of "_instance" in _type, for names covering several Oscar types
    instance: Optional[str] = None
    # obj → name to write, for Sage types matching several Oscar names
    name: Optional[Callable] = None

_handlers: list = []          # [(python_type, TypeHandler)]
_load_handlers: dict = {}     # oscar_name → TypeHandler

def register(python_type, oscar_name, *,
             uses_id: bool = False,
             params=None,
             save_data=None,
             load_fn=None,
             instance=None,
             name=None,
             also_loads=()):
    handler = TypeHandler(oscar_name, uses_id, params, save_data, load_fn, instance, name)
    _handlers.append((python_type, handler))
    for n in (oscar_name, *also_loads):
        _load_handlers[n] = handler

def _find_handler(obj) -> Optional[TypeHandler]:
    """Find handler by isinstance check (MRO-aware via list order)."""
    from sage.rings.finite_rings.integer_mod import IntegerMod_abstract
    from sage.rings.finite_rings.finite_field_base import FiniteField
    from sage.rings.finite_rings.integer_mod_ring import IntegerModRing_generic

    # GF(p) is also an IntegerModRing, and IntegerMod_abstract is used for both
    # GF(p) elements and ZZ/nZ elements; disambiguate by (parent) type.
    if isinstance(obj, FiniteField):
        return _load_handlers.get("FiniteField")
    if isinstance(obj, IntegerMod_abstract):
        if isinstance(obj.parent(), FiniteField):
            return _load_handlers.get("FiniteFieldElement")
        else:
            return _load_handlers.get("ZZModRingElem")

    for python_type, handler in _handlers:
        if isinstance(obj, python_type):
            return handler
    return None

################################################################################
# SerializerState and I/O helpers

class SerializerState:
    def __init__(self, io, with_attrs: bool):
        self.new_level_entry = True
        self.refs: list = []
        self.io = io
        self.key = None
        self.with_attrs = with_attrs

    def begin_node(self):
        if not self.new_level_entry:
            self.io.write(",")
        else:
            self.new_level_entry = False
        if self.key is not None:
            self.io.write(f'"{self.key}":')
            self.key = None

    def begin_dict_node(self):
        self.begin_node()
        self.io.write("{")

    def end_dict_node(self):
        self.io.write("}")
        self.new_level_entry = False

    def begin_array_node(self):
        self.begin_node()
        self.io.write("[")

    def end_array_node(self):
        self.io.write("]")
        self.new_level_entry = False

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

def save_as_ref(s, obj) -> str:
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

################################################################################
# Deserialization state

class DeserializerState:
    def __init__(self, obj, refs=None):
        self.obj = obj
        self.refs = refs

def deserializer_open(io):
    obj = json.load(io)
    return DeserializerState(obj, refs=obj.get("_refs"))

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
# Namespace header

def get_oscar_serialization_version() -> dict:
    v = VERSION_NUMBER
    return {"Oscar": [OSCAR_URL, f"{v[0]}.{v[1]}.{v[2]}"],
            "mrdi": [MRDI_URL, MRDI_VERSION]}

################################################################################
# Serialization dispatch

def _write_inline_typed_object(s, obj):
    """Write type + data of obj in the current dict context.
    Used for inline (non-uses_id) params."""
    handler = _find_handler(obj)
    if handler is None:
        raise TypeError(f"No MRDI handler registered for {type(obj).__name__}")
    _write_type_field(s, obj, handler)
    if handler.save_data:
        handler.save_data(s, obj, "data")

def _write_type_field(s, obj, handler: TypeHandler):
    """Write the _type field for obj: a bare name for mrdi types without
    params, otherwise a dict with name, namespace tag, _instance and params."""
    name = handler.name(obj) if handler.name else handler.oscar_name
    params = handler.params(obj) if handler.params else None
    if params is None and name in MRDI_TYPES and handler.instance is None:
        save_data_basic(s, name, "_type")
        return

    def write_type():
        save_data_basic(s, name, "name")
        if name not in MRDI_TYPES:
            save_data_basic(s, "Oscar", "_ns")
        if handler.instance is not None:
            save_data_basic(s, handler.instance, "_instance")
        if params is not None:
            _write_params(s, params)
    save_data_dict(write_type, s, "_type")

def _write_params(s, p):
    """Params are a ref (UUID) if their type uses ids, as in Oscar, else inline."""
    handler = _find_handler(p)
    if handler is None:
        raise TypeError(f"No MRDI handler registered for {type(p).__name__}")
    if handler.uses_id:
        save_data_basic(s, save_as_ref(s, p), "params")
    else:
        save_data_dict(lambda: _write_inline_typed_object(s, p), s, "params")

def save_typed_object(s, obj, key=None):
    handler = _find_handler(obj)
    if handler is None:
        raise TypeError(f"No MRDI handler registered for {type(obj).__name__}")

    def save_body():
        _write_type_field(s, obj, handler)
        if handler.save_data:
            handler.save_data(s, obj, "data")

    if key is None:
        save_body()
    else:
        save_data_dict(save_body, s, key)

def handle_refs(s):
    if s.refs:
        def write_refs():
            i = 0
            while i < len(s.refs):  # writing a ref may add more refs
                r = s.refs[i]
                save_typed_object(s, global_serializer_state.id_to_obj[r], key=str(r))
                i += 1
        save_data_dict(write_refs, s, "_refs")

################################################################################
# Deserialization dispatch

def load_type_params(s) -> dict:
    type_field = s.obj.get("_type") if isinstance(s.obj, dict) else s.obj
    if isinstance(type_field, str):
        return {"type_str": OLD_NAMES.get(type_field, type_field), "params": None}

    # type_field is a dict: {"name": "...", "_ns"?: ..., "_instance"?: ..., "params"?: ...}
    name = OLD_NAMES.get(type_field["name"], type_field["name"])
    obj = s.obj
    params_val = type_field.get("params")
    if params_val is None:
        return {"type_str": name, "params": None}

    s.obj = params_val
    params = load_typed_object(s)
    s.obj = obj
    return {"type_str": name, "params": params}

def load_typed_object(s):
    if isinstance(s.obj, str):
        return load_ref(s)
    tp = load_type_params(s)
    return _load_dispatch(s, tp["type_str"], tp["params"])

def _load_dispatch(s, type_str: str, params):
    handler = _load_handlers.get(type_str)
    if handler is None:
        raise ValueError(f"No MRDI loader for Oscar type {type_str!r}")
    return handler.load_fn(s, params)

################################################################################
# High-level API

def save(io, obj, with_attrs=True):
    s = SerializerState(io, with_attrs)

    def body():
        save_data_json(s, get_oscar_serialization_version(), key="_ns")
        save_typed_object(s, obj)
        handle_refs(s)

    save_data_dict(body, s)

def save_file(filename: str, obj: Any, with_attrs=True):
    dirpath = os.path.dirname(os.path.abspath(filename))
    tmp = tempfile.NamedTemporaryFile(delete=False, dir=dirpath)
    try:
        with open(tmp.name, "w") as f:
            save(f, obj, with_attrs=with_attrs)
        shutil.move(tmp.name, filename)
    except Exception:
        os.unlink(tmp.name)
        raise

def load(io):
    s = deserializer_open(io)
    return load_typed_object(s)

def load_file(filename: str):
    with open(filename, "r") as f:
        return load(f)
