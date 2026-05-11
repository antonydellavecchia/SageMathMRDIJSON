import io
import pytest
from sage.all import QQ, MatrixSpace

from mrdi import save, load, save_file, load_file, reset_global_serializer_state


def roundtrip(obj):
    reset_global_serializer_state()
    buf = io.StringIO()
    save(buf, obj)
    buf.seek(0)
    reset_global_serializer_state()
    return load(buf)


class TestMatrixRoundtrip:
    def test_integer_square(self):
        M = MatrixSpace(QQ, 2, 2)
        m = M([[1, 2], [3, 4]])
        assert roundtrip(m) == m

    def test_integer_rectangular(self):
        M = MatrixSpace(QQ, 2, 3)
        m = M([[1, 2, 3], [4, 5, 6]])
        assert roundtrip(m) == m

    def test_rational_entries(self):
        M = MatrixSpace(QQ, 2, 2)
        m = M([[QQ(1) / 3, QQ(1) / 2], [QQ(-5) / 7, QQ(0)]])
        assert roundtrip(m) == m

    def test_negative_entries(self):
        M = MatrixSpace(QQ, 2, 2)
        m = M([[-1, -2], [-3, -4]])
        assert roundtrip(m) == m

    def test_zero_matrix(self):
        M = MatrixSpace(QQ, 2, 2)
        m = M.zero()
        assert roundtrip(m) == m

    def test_identity(self):
        M = MatrixSpace(QQ, 3, 3)
        m = M.identity_matrix()
        assert roundtrip(m) == m

    def test_1x1(self):
        M = MatrixSpace(QQ, 1, 1)
        m = M([[QQ(7) / 11]])
        assert roundtrip(m) == m

    def test_parent_preserved(self):
        M = MatrixSpace(QQ, 2, 3)
        m = M([[1, 2, 3], [4, 5, 6]])
        m2 = roundtrip(m)
        assert m2.parent() == M

    def test_file_roundtrip(self, tmp_path):
        M = MatrixSpace(QQ, 2, 2)
        m = M([[1, 2], [3, 4]])
        path = str(tmp_path / "m.mrdi")
        reset_global_serializer_state()
        save_file(path, m)
        reset_global_serializer_state()
        assert load_file(path) == m
