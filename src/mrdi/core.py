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

VERSION_NUMBER = (1, 5, 0)

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
    oscar_name: str
    uses_id: bool
    # (s, obj) → writes "params" field; None means no params (_type is plain string)
    get_params: Optional[Callable]
    # (s, obj, key) → writes data under key; None means no data
    save_data: Optional[Callable]
    # (s, params) → Sage object
    load_fn: Callable

_handlers: list = []          # [(python_type, TypeHandler)]
_load_handlers: dict = {}     # oscar_name → TypeHandler

def register(python_type, oscar_name, *,
             uses_id: bool = False,
             get_params=None,
             save_data=None,
             load_fn=None):
    handler = TypeHandler(oscar_name, uses_id, get_params, save_data, load_fn)
    _handlers.append((python_type, handler))
    _load_handlers[oscar_name] = handler

def _find_handler(obj) -> Optional[TypeHandler]:
    """Find handler by isinstance check (MRO-aware via list order)."""
    from sage.rings.finite_rings.integer_mod import IntegerMod_abstract
    from sage.rings.finite_rings.finite_field_base import FiniteField
    from sage.rings.finite_rings.integer_mod_ring import IntegerModRing_generic

    # IntegerMod_abstract is used for both GF(p) elements and ZZ/nZ elements;
    # disambiguate by parent type.
    if isinstance(obj, IntegerMod_abstract):
        if isinstance(obj.parent(), FiniteField):
            return _load_handlers.get("fpFieldElem")
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
    return {"Oscar": ["https://github.com/oscar-system/Oscar.jl", f"{v[0]}.{v[1]}.{v[2]}"]}

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
    """Write the _type field for obj."""
    if handler.get_params is None:
        save_data_basic(s, handler.oscar_name, "_type")
    else:
        def write_type():
            save_data_basic(s, handler.oscar_name, "name")
            handler.get_params(s, obj)
        save_data_dict(write_type, s, "_type")

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
            for r in list(s.refs):  # copy: save_typed_object may add more refs
                save_typed_object(s, global_serializer_state.id_to_obj[r], key=str(r))
        save_data_dict(write_refs, s, "_refs")

################################################################################
# Deserialization dispatch

def load_type_params(s) -> dict:
    type_field = s.obj.get("_type") if isinstance(s.obj, dict) else s.obj
    if isinstance(type_field, str):
        return {"type_str": type_field, "params": None}

    # type_field is a dict: {"name": "...", "params": ...}
    obj = s.obj
    params_val = type_field.get("params")
    if params_val is None:
        return {"type_str": type_field["name"], "params": None}

    s.obj = params_val
    params = load_typed_object(s)
    s.obj = obj
    return {"type_str": type_field["name"], "params": params}

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
# Param helpers (used by type modules)

def get_params_inline(s, ring_obj):
    """Write params as inline typed object (for non-uses_id base rings)."""
    def write():
        _write_inline_typed_object(s, ring_obj)
    save_data_dict(write, s, "params")

def get_params_ref(s, parent_obj) -> str:
    """Register parent as a ref and write UUID as params. Returns UUID string."""
    ref = save_as_ref(s, parent_obj)
    save_data_basic(s, ref, "params")
    return ref

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
