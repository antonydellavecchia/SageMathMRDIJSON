import io
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from mrdi import save, load


def roundtrip(obj):
    buf = io.StringIO()
    save(buf, obj)
    buf.seek(0)
    return load(buf)


@pytest.fixture(autouse=True)
def clear_state():
    from mrdi import reset_global_serializer_state
    reset_global_serializer_state()
    yield
    reset_global_serializer_state()
