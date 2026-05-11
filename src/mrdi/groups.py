"""
Serializers for group types.
Mirrors Oscar.jl's Serialization/Groups.jl (PermGroup subset).

Registered types:
  PermGroup    ↔  sage PermutationGroup_generic  (uses_id)
  PermGroupElem ↔ sage PermutationGroupElement
"""

from sage.groups.perm_gps.permgroup import PermutationGroup_generic
from sage.groups.perm_gps.permgroup_element import PermutationGroupElement

from mrdi.core import (
    register, save_data_basic, save_data_json, save_data_dict,
    get_params_ref,
)

# ---------------------------------------------------------------------------
# PermGroup  (uses_id)

def _save_perm_group(s, obj, key):
    def _write():
        save_data_basic(s, str(obj.degree()), "degree")
        gens_data = [list(g.tuple()) for g in obj.gens()]
        save_data_json(s, gens_data, "gens")
    save_data_dict(_write, s, key)

def _load_perm_group(s, params):
    from sage.all import PermutationGroup
    data = s.obj["data"]
    degree = int(data["degree"])
    gens = data["gens"]
    return PermutationGroup(gens, domain=list(range(1, degree + 1)))

register(
    PermutationGroup_generic, "PermGroup",
    uses_id=True,
    save_data=_save_perm_group,
    load_fn=_load_perm_group,
)

# ---------------------------------------------------------------------------
# PermGroupElem

def _get_params_perm_elem(s, obj):
    get_params_ref(s, obj.parent())

def _save_perm_elem(s, obj, key):
    save_data_json(s, list(obj.tuple()), key)

def _load_perm_elem(s, params):
    images = s.obj.get("data", s.obj)
    return params(images)

register(
    PermutationGroupElement, "PermGroupElem",
    get_params=_get_params_perm_elem,
    save_data=_save_perm_elem,
    load_fn=_load_perm_elem,
)
