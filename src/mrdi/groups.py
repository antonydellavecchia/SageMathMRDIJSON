"""
Serializers for group types.
Mirrors Oscar.jl's Serialization/Groups.jl (PermGroup subset).

Registered types (Oscar namespace):
  PermGroup    ↔  sage PermutationGroup_generic  (uses_id)
  PermGroupElem ↔ sage PermutationGroupElement
"""

from sage.groups.perm_gps.permgroup import PermutationGroup_generic
from sage.groups.perm_gps.permgroup_element import PermutationGroupElement

from mrdi.core import register, save_data_json, save_data_dict

# ---------------------------------------------------------------------------
# PermGroup  (uses_id)

def _save_perm_group(s, obj, key):
    def _write():
        save_data_json(s, int(obj.degree()), "degree")
        save_data_json(s, [[int(i) for i in g.tuple()] for g in obj.gens()], "gens")
    save_data_dict(_write, s, key)

def _load_perm_group(s, params):
    from sage.all import PermutationGroup
    data = s.obj["data"]
    degree = int(data["degree"])
    gens = [[int(i) for i in g] for g in data["gens"]]
    return PermutationGroup(gens, domain=list(range(1, degree + 1)))

register(
    PermutationGroup_generic, "PermGroup",
    uses_id=True,
    save_data=_save_perm_group,
    load_fn=_load_perm_group,
)

# ---------------------------------------------------------------------------
# PermGroupElem

def _save_perm_elem(s, obj, key):
    save_data_json(s, [int(i) for i in obj.tuple()], key)

def _load_perm_elem(s, params):
    return params([int(i) for i in s.obj.get("data", s.obj)])

register(
    PermutationGroupElement, "PermGroupElem",
    params=lambda obj: obj.parent(),
    save_data=_save_perm_elem,
    load_fn=_load_perm_elem,
)
