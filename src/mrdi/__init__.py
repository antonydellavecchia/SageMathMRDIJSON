"""
sage-mrdi: MRDI serialization for Sage mathematical objects.

Oscar-compatible .mrdi format (version 1.5).
"""

# Import type modules to trigger handler registration
import mrdi.basic_types  # noqa: F401
import mrdi.rings        # noqa: F401
import mrdi.fields       # noqa: F401
import mrdi.groups       # noqa: F401

from mrdi.core import (
    save,
    load,
    save_file,
    load_file,
    reset_global_serializer_state,
)

__all__ = [
    "save",
    "load",
    "save_file",
    "load_file",
    "reset_global_serializer_state",
]
