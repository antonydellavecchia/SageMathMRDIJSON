import io
import pytest
from sage.all import QQ, MatrixSpace

from mrdi import save, load, save_file, load_file


def roundtrip(obj):
    buf = io.StringIO()
    save(buf, obj)
    buf.seek(0)
    return load(buf)


class TestMatrixRoundtrip:
    def test_integer_square(self):
        m = MatrixSpace(QQ, 2, 2)([[1, 2], [3, 4]])
        assert roundtrip(m) == m

    def test_integer_rectangular(self):
        m = MatrixSpace(QQ, 2, 3)([[1, 2, 3], [4, 5, 6]])
        assert roundtrip(m) == m

    def test_rational_entries(self):
        M = MatrixSpace(QQ, 2, 2)
        m = M([[QQ(1) / 3, QQ(1) / 2], [QQ(-5) / 7, QQ(0)]])
        assert roundtrip(m) == m

    def test_negative_entries(self):
        m = MatrixSpace(QQ, 2, 2)([[-1, -2], [-3, -4]])
        assert roundtrip(m) == m

    def test_zero_matrix(self):
        m = MatrixSpace(QQ, 2, 2).zero()
        assert roundtrip(m) == m

    def test_identity(self):
        m = MatrixSpace(QQ, 3, 3).identity_matrix()
        assert roundtrip(m) == m

    def test_1x1(self):
        m = MatrixSpace(QQ, 1, 1)([[QQ(7) / 11]])
        assert roundtrip(m) == m

    def test_parent_preserved(self):
        M = MatrixSpace(QQ, 2, 3)
        m = M([[1, 2, 3], [4, 5, 6]])
        assert roundtrip(m).parent() == M

    def test_file_roundtrip(self, tmp_path):
        m = MatrixSpace(QQ, 2, 2)([[1, 2], [3, 4]])
        path = str(tmp_path / "m.mrdi")
        save_file(path, m)
        assert load_file(path) == m
