import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

@pytest.fixture(autouse=True)
def clear_state():
    from mrdi import reset_global_serializer_state
    reset_global_serializer_state()
    yield
    reset_global_serializer_state()
